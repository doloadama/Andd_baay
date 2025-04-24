# Use a Debian-based Python image
FROM python:3.13-slim

# Set the working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y gcc g++ libffi-dev

# Copy the project files
COPY . /app

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose the port
EXPOSE 8000

# Run the server
CMD ["gunicorn", "Anndd_Baayi.wsgi:application", "--bind", "0.0.0.0:8000"]
