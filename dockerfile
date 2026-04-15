FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN pip install --upgrade pip

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

# Build-time static collection needs a SECRET_KEY (settings enforce it).
# This value is only used during image build, not at runtime.
RUN DJANGO_SECRET_KEY=build-time-only python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "Andd_Baayi.wsgi:application", "--bind", "0.0.0.0:8000"]
