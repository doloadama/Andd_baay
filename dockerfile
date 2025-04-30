# Use a Debian-based Python image
FROM python:alpine

# Set the working directory
WORKDIR /app

# Install system dependencies
RUN apk add --no-cache gcc g++ libffi-dev

# Copy the project files
COPY . /app

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Collect static files (if applicable)
RUN python manage.py collectstatic --noinput

# Expose the port
EXPOSE 8000

# Run the server
CMD ["python", "manage.py", "runserver", "--bind", "0.0.0.0:8000"]