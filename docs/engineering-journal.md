## Sprint 2

### Learned

Docker layer caching depends on instruction order.

### Mistake

Forgot to save the Dockerfile before building.

### Lesson

Always verify the artifact exists before debugging Docker.

### Decision

Use python:3.12-slim as the base image to reduce image size and attack surface.