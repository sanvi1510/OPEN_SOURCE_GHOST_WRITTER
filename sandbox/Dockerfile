FROM python:3.11-slim

# No extra packages – keep the image minimal and secure.
WORKDIR /sandbox

# Drop to a non-root user for safety.
RUN useradd --create-home sandboxuser
USER sandboxuser

# Default entrypoint: run whatever Python command is passed.
ENTRYPOINT ["python"]
