"""
Synthetic Training Data Generator for Voice Agent Fine-Tuning.

Generates diverse phone conversations for training the voice agent LLM.
Uses a large model (or the base model itself) to create varied scenarios.

Usage:
  python scripts/voice-agent/generate_training_data.py \
    --output data/voice_agent_training.jsonl \
    --count 500 \
    --llm-url http://localhost:8000/v1

Output format (JSONL, one conversation per line):
{
  "conversations": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."},
    ...
  ]
}
"""

import argparse
import json
import random
import sys

import httpx

BUSINESS_TYPES = [
    "dental office", "law firm", "auto repair shop", "hair salon",
    "medical clinic", "real estate agency", "accounting firm",
    "veterinary clinic", "restaurant", "fitness studio",
    "consulting firm", "insurance agency", "plumbing company",
    "photography studio", "tutoring center",
]

SCENARIOS = [
    "schedule a new appointment",
    "reschedule an existing appointment",
    "cancel an appointment",
    "ask about business hours and services",
    "make a complaint about service",
    "ask about pricing",
    "request a callback from a specialist",
    "leave a message for the owner",
    "ask for directions or location",
    "inquire about availability this week",
    "follow up on a previous visit",
    "request an emergency appointment",
    "ask about insurance or payment options",
    "book for multiple people",
    "ask about cancellation policy",
]

CALLER_PERSONALITIES = [
    "polite and straightforward",
    "in a rush and brief",
    "elderly and needs things repeated",
    "confused about what they need",
    "chatty and goes off-topic",
    "frustrated with a previous experience",
    "professional and efficient",
    "nervous first-time caller",
    "calling on behalf of someone else",
    "non-native English speaker (clear but simple phrasing)",
]

SYSTEM_PROMPT_TEMPLATE = """You are a professional phone receptionist for {business_name}, a {business_type}.

Your responsibilities:
- Answer calls warmly and professionally
- Schedule, reschedule, and cancel appointments
- Capture the caller's name, phone number, and reason for calling
- Answer questions about services, hours, and pricing
- Take messages when needed
- Set callback reminders if you cannot help directly

Business hours: Monday-Friday 9:00 AM - 5:00 PM
Appointment duration: 30 minutes
Location: 123 Main Street

Always:
- Confirm details before taking action
- Be concise (this is a phone call)
- Ask for spelling of names if unclear
- Offer alternatives if requested time is unavailable"""

GENERATION_PROMPT = """Generate a realistic phone conversation between a CALLER and an AI RECEPTIONIST for a {business_type} called "{business_name}".

Scenario: The caller wants to {scenario}.
Caller personality: {personality}
Conversation should be {length} turns (each turn = one caller line + one agent line).

Important:
- Make it sound natural, like a real phone call
- Include filler words, corrections, and interruptions where appropriate
- The receptionist should use function calls when needed (scheduling, checking availability)
- End the conversation naturally

Format as a JSON array of message objects:
[
  {{"role": "user", "content": "caller's words"}},
  {{"role": "assistant", "content": "receptionist's response"}},
  ...
]

Generate the conversation now. Respond ONLY with the JSON array."""


def generate_business_name(business_type):
    """Generate a plausible business name."""
    prefixes = ["Premier", "City", "Valley", "Oak", "Summit", "Harbor", "Metro", "Pine"]
    suffixes = {
        "dental office": ["Dental", "Dental Care", "Family Dentistry"],
        "law firm": ["Law Group", "Legal Associates", "& Partners"],
        "auto repair shop": ["Auto", "Auto Care", "Motors"],
        "hair salon": ["Hair Studio", "Salon", "Style Bar"],
        "medical clinic": ["Medical Center", "Health Clinic", "Wellness"],
        "real estate agency": ["Realty", "Real Estate", "Properties"],
        "accounting firm": ["Accounting", "CPA Group", "Financial Services"],
        "veterinary clinic": ["Vet Clinic", "Animal Hospital", "Pet Care"],
        "restaurant": ["Kitchen", "Bistro", "Grill"],
        "fitness studio": ["Fitness", "Gym", "Wellness Studio"],
        "consulting firm": ["Consulting", "Advisory Group", "Solutions"],
        "insurance agency": ["Insurance", "Insurance Group", "Coverage"],
        "plumbing company": ["Plumbing", "Plumbing & Heating", "Pipe Works"],
        "photography studio": ["Photography", "Photo Studio", "Imaging"],
        "tutoring center": ["Learning Center", "Tutoring", "Academy"],
    }
    prefix = random.choice(prefixes)
    suffix = random.choice(suffixes.get(business_type, ["Services"]))
    return f"{prefix} {suffix}"


def generate_conversation(llm_url, model):
    """Generate a single training conversation."""
    business_type = random.choice(BUSINESS_TYPES)
    business_name = generate_business_name(business_type)
    scenario = random.choice(SCENARIOS)
    personality = random.choice(CALLER_PERSONALITIES)
    length = random.randint(4, 12)

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        business_name=business_name, business_type=business_type
    )

    gen_prompt = GENERATION_PROMPT.format(
        business_type=business_type,
        business_name=business_name,
        scenario=scenario,
        personality=personality,
        length=length,
    )

    with httpx.Client(timeout=120) as client:
        resp = client.post(
            f"{llm_url}/chat/completions",
            json={
                "model": model,
                "messages": [{"role": "user", "content": gen_prompt}],
                "temperature": 0.9,
                "max_tokens": 2048,
            },
        )
        resp.raise_for_status()

    content = resp.json()["choices"][0]["message"]["content"]

    # Parse the generated conversation
    try:
        # Try to extract JSON from the response
        start = content.find("[")
        end = content.rfind("]") + 1
        if start >= 0 and end > start:
            messages = json.loads(content[start:end])
        else:
            return None
    except json.JSONDecodeError:
        return None

    # Build the training example
    conversation = [{"role": "system", "content": system_prompt}]
    for msg in messages:
        if msg.get("role") in ("user", "assistant") and msg.get("content"):
            conversation.append({"role": msg["role"], "content": msg["content"]})

    if len(conversation) < 4:
        return None

    return {
        "conversations": conversation,
        "metadata": {
            "business_type": business_type,
            "scenario": scenario,
            "personality": personality,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic voice agent training data")
    parser.add_argument("--output", default="data/voice_agent_training.jsonl")
    parser.add_argument("--count", type=int, default=500)
    parser.add_argument("--llm-url", default="http://localhost:8000/v1")
    parser.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct-AWQ")
    args = parser.parse_args()

    import os
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)

    generated = 0
    failed = 0

    with open(args.output, "w") as f:
        while generated < args.count:
            try:
                example = generate_conversation(args.llm_url, args.model)
                if example:
                    f.write(json.dumps(example) + "\n")
                    generated += 1
                    if generated % 10 == 0:
                        print(f"Generated {generated}/{args.count} conversations...")
                else:
                    failed += 1
            except Exception as e:
                failed += 1
                print(f"Error: {e}", file=sys.stderr)

            if failed > args.count * 2:
                print("Too many failures, stopping.", file=sys.stderr)
                break

    print(f"Done. Generated {generated} conversations, {failed} failures.")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()
