import logging

from celery import shared_task

logger = logging.getLogger("apps.agents")


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    soft_time_limit=300,
    time_limit=600,
    acks_late=True,
    name="apps.agents.tasks.run_agent_task",
)
def run_agent_task(self, agent_run_id: str):
    """Execute an agent run asynchronously."""
    from apps.agents.engine import AgentEngine
    from apps.agents.models import AgentRun

    try:
        agent_run = AgentRun.objects.get(id=agent_run_id)
        if agent_run.status not in ("pending", "running"):
            logger.info(f"Agent run {agent_run_id} is {agent_run.status}, skipping.")
            return

        engine = AgentEngine()
        engine.run(agent_run)
        logger.info(f"Agent run {agent_run_id} finished with status: {agent_run.status}")

    except Exception as exc:
        logger.error(f"Agent task failed for {agent_run_id}: {exc}")
        try:
            agent_run = AgentRun.objects.get(id=agent_run_id)
            agent_run.status = "failed"
            agent_run.error_message = str(exc)[:2000]
            agent_run.save(update_fields=["status", "error_message"])
        except Exception:
            pass
        raise self.retry(exc=exc) from None


@shared_task(
    bind=True,
    max_retries=1,
    soft_time_limit=120,
    time_limit=180,
    name="apps.agents.tasks.resume_agent_task",
)
def resume_agent_task(self, agent_run_id: str):
    """Resume a paused agent after approval."""
    from apps.agents.engine import AgentEngine
    from apps.agents.models import AgentRun

    try:
        agent_run = AgentRun.objects.get(id=agent_run_id)
        if agent_run.status != "paused":
            logger.info(f"Agent run {agent_run_id} is not paused, skipping resume.")
            return

        engine = AgentEngine()
        engine.resume(agent_run)
        logger.info(f"Agent run {agent_run_id} resumed and completed.")

    except Exception as exc:
        logger.error(f"Resume failed for {agent_run_id}: {exc}")
        raise self.retry(exc=exc) from exc


@shared_task(name="apps.agents.tasks.run_scheduled_agents")
def run_scheduled_agents():
    """Cron task: create and run agent runs for scheduled agent types."""
    from apps.agents.agent_types import AGENT_CONFIGS
    from apps.agents.models import AgentRun
    from apps.websites.models import Website

    scheduled_types = [
        key for key, config in AGENT_CONFIGS.items()
        if config["default_trigger"] == "scheduled"
    ]

    for website in Website.objects.filter(is_active=True, pixel_verified=True):
        for agent_type in scheduled_types:
            # Don't create a new run if one is already pending/running
            existing = AgentRun.objects.filter(
                website=website,
                agent_type=agent_type,
                status__in=["pending", "running"],
            ).exists()

            if not existing:
                config = AGENT_CONFIGS[agent_type]
                agent_run = AgentRun.objects.create(
                    website=website,
                    agent_type=agent_type,
                    trigger="scheduled",
                    requires_approval=config.get("requires_approval", False),
                )
                run_agent_task.delay(str(agent_run.id))
                logger.info(f"Scheduled {agent_type} agent for website {website.id}")
