# start by pulling the ubuntu image
FROM python:3.12.8

# Install required dependencies for building PyAudio
RUN apt-get update && apt-get install -y \
    python3-distutils \
    && rm -rf /var/lib/apt/lists/*
# Create Work directory
WORKDIR /app

# Copy the Code to Working Directory
COPY . /app

# Installing Requirements.txt
RUN pip install --upgrade -r requirements.txt --no-cache-dir

# Expose Port 80
EXPOSE 8080

# configure the container to run in an executed manner
ENTRYPOINT [ "python" ]

# Run the Pyscrapy API Application
CMD ["app.py" ]

