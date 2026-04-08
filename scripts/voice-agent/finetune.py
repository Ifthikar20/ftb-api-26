"""
LoRA Fine-Tuning Script for Voice Agent LLM.

Fine-tunes Qwen2.5-7B-Instruct using Unsloth (2x faster, 60% less VRAM).

Requirements:
  pip install unsloth transformers trl datasets

Hardware:
  - Minimum: A10G (24GB) or RTX 4090 (24GB)
  - Also works on: T4 (16GB) with smaller batch size
  - Training time: ~1-2 hours for 500 examples, 3 epochs

Usage:
  python scripts/voice-agent/finetune.py \
    --data data/voice_agent_training.jsonl \
    --output models/voice-agent-lora \
    --base-model Qwen/Qwen2.5-7B-Instruct \
    --epochs 3

After training, merge the LoRA adapter:
  python scripts/voice-agent/finetune.py --merge \
    --base-model Qwen/Qwen2.5-7B-Instruct \
    --lora models/voice-agent-lora \
    --output models/voice-agent-merged
"""

import argparse
import json
import sys


def train(args):
    """Run LoRA fine-tuning with Unsloth."""
    try:
        from unsloth import FastLanguageModel
    except ImportError:
        print("ERROR: Unsloth not installed. Run: pip install unsloth")
        sys.exit(1)

    import torch
    from datasets import Dataset
    from transformers import TrainingArguments
    from trl import SFTTrainer

    print(f"Loading base model: {args.base_model}")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=args.base_model,
        max_seq_length=4096,
        dtype=None,  # Auto-detect (float16 or bfloat16)
        load_in_4bit=True,
    )

    print("Adding LoRA adapters...")
    model = FastLanguageModel.get_peft_model(
        model,
        r=args.lora_rank,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
        lora_alpha=args.lora_rank,
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
    )

    # Load and format dataset
    print(f"Loading training data from: {args.data}")
    examples = []
    with open(args.data) as f:
        for line in f:
            obj = json.loads(line.strip())
            conversations = obj["conversations"]
            text = tokenizer.apply_chat_template(
                conversations,
                tokenize=False,
                add_generation_prompt=False,
            )
            examples.append({"text": text})

    print(f"Loaded {len(examples)} training examples")
    dataset = Dataset.from_list(examples)

    # Training
    print(f"Starting training for {args.epochs} epochs...")
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=4096,
        args=TrainingArguments(
            per_device_train_batch_size=args.batch_size,
            gradient_accumulation_steps=args.grad_accum,
            warmup_steps=10,
            num_train_epochs=args.epochs,
            learning_rate=2e-4,
            fp16=not torch.cuda.is_bf16_supported(),
            bf16=torch.cuda.is_bf16_supported(),
            logging_steps=10,
            save_strategy="epoch",
            output_dir=args.output,
            optim="adamw_8bit",
            seed=42,
        ),
    )

    trainer.train()

    # Save LoRA adapter
    print(f"Saving LoRA adapter to: {args.output}")
    model.save_pretrained(args.output)
    tokenizer.save_pretrained(args.output)

    print("Training complete!")
    print("\nTo merge into a full model, run:")
    print("  python scripts/voice-agent/finetune.py --merge \\")
    print(f"    --base-model {args.base_model} \\")
    print(f"    --lora {args.output} \\")
    print("    --output models/voice-agent-merged")
    print("\nTo serve with vLLM:")
    print("  python -m vllm.entrypoints.openai.api_server \\")
    print("    --model models/voice-agent-merged \\")
    print("    --quantization awq --host 0.0.0.0 --port 8000")


def merge(args):
    """Merge LoRA adapter into the base model for deployment."""
    try:
        from unsloth import FastLanguageModel
    except ImportError:
        print("ERROR: Unsloth not installed. Run: pip install unsloth")
        sys.exit(1)

    print(f"Loading base model: {args.base_model}")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=args.base_model,
        max_seq_length=4096,
        dtype=None,
        load_in_4bit=True,
    )

    print(f"Loading LoRA adapter from: {args.lora}")
    from peft import PeftModel

    model = PeftModel.from_pretrained(model, args.lora)

    print(f"Merging and saving to: {args.output}")
    model.save_pretrained_merged(
        args.output,
        tokenizer,
        save_method="merged_16bit",
    )

    print("Merge complete!")
    print("\nTo quantize for deployment (AWQ):")
    print("  pip install autoawq")
    print("  python -c \"")
    print("    from awq import AutoAWQForCausalLM")
    print(f"    model = AutoAWQForCausalLM.from_pretrained('{args.output}')\"")
    print("    model.quantize(tokenizer, quant_config={'w_bit': 4, 'q_group_size': 128})")
    print(f"    model.save_quantized('{args.output}-awq')")


def main():
    parser = argparse.ArgumentParser(description="Fine-tune voice agent LLM with LoRA")
    parser.add_argument("--merge", action="store_true", help="Merge LoRA into base model")

    # Training args
    parser.add_argument("--data", default="data/voice_agent_training.jsonl")
    parser.add_argument("--output", default="models/voice-agent-lora")
    parser.add_argument("--base-model", default="Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--grad-accum", type=int, default=4)
    parser.add_argument("--lora-rank", type=int, default=16)

    # Merge args
    parser.add_argument("--lora", default="models/voice-agent-lora")

    args = parser.parse_args()

    if args.merge:
        merge(args)
    else:
        train(args)


if __name__ == "__main__":
    main()
