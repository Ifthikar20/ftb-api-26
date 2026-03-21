# Project Rules

## Communication Style

- Do not use emojis in any output, file content, commit messages, comments, or documentation.
- Maintain a professional, concise tone in all responses and written content.
- Use plain language. Avoid filler phrases and unnecessary preamble.

## Application Execution

- Do not start, run, or serve the application. This includes `python manage.py runserver`, `npm start`, `yarn dev`, `uvicorn`, `gunicorn`, `celery worker`, `celery beat`, or any equivalent command.
- Do not attempt to verify behavior by running a live server. Use tests and static analysis instead.
- If a task requires running the application, stop and inform the user rather than proceeding.

## Development Standards

- Write and run tests to verify correctness. Do not assume code works without test coverage.
- Use static analysis tools (linters, type checkers) where available.
- Do not introduce code that bypasses security checks or adds unnecessary complexity.
