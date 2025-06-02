FROM python:3.12

WORKDIR /code


# Install system dependencies
COPY ./requirements.txt ./requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# opencv 
RUN apt-get update && apt-get install -y libglib2.0-0 libgl1-mesa-glx && rm -rf /var/lib/apt/lists/*

# Copy the 'static' folders and files
COPY ./static ./static
COPY ./templates ./templates
COPY ./models ./models
COPY ./apis ./apis
COPY ./videos ./videos

# copy changing files 
COPY ./modules ./modules
COPY ./main.py ./main.py

#expose the port the app runs on
EXPOSE 80

# Run the application
CMD ["fastapi", "run", "main.py", "--port", "80"]
