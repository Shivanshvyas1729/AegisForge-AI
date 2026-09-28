# Use the lightweight Alpine Linux Python image
FROM python:3.9-alpine

# Set the working directory
WORKDIR /sandbox

# Install system dependencies required for building pandas and python-docx on Alpine
RUN apk add --no-cache \
    build-base \
    libffi-dev \
    libxml2-dev \
    libxslt-dev \
    jpeg-dev \
    zlib-dev

# Install Python packages that the AI might need for data analysis and document generation
# We install these here so the container doesn't need internet access at runtime
RUN pip install --no-cache-dir \
    python-docx \
    pandas \
    numpy

# Create writable output directory for sandboxuser
RUN mkdir -p /output && chmod 777 /output

# Set strict permissions (optional security hardening)
RUN adduser -D sandboxuser
USER sandboxuser

# By default, run the python interpreter
CMD ["python"]
