# Use a CUDA-enabled base image
FROM pytorch/pytorch:2.2.1-cuda12.1-cudnn8-runtime

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y 
    git 
    && rm -rf /var/lib/apt/lists/*

# Copy requirements from root
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install API-specific dependencies
RUN pip install --no-cache-dir fastapi uvicorn sse-starlette gcsfs

# Copy API source code
COPY app/api/ .

# Expose port
EXPOSE 8080

# Use uvicorn to run the app
CMD ["uvicorn", "main.py", "--host", "0.0.0.0", "--port", "8080"]
