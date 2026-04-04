# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . .

# Change ownership of /app
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Define environment variable
ENV FLASK_APP=ett_gns_app

# Run the application using Gunicorn
CMD ["gunicorn", "-w", "4", "--threads", "2", "-b", "0.0.0.0:5000", "run:app"]
