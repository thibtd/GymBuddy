FROM python:3.11



ENV PYTHONUNBUFFERED=1

WORKDIR /code

COPY models/pose_landmarker_lite.task models/pose_landmarker_lite.task
COPY ./requirements.txt ./code/requirements.txt
COPY ./makefile /code/makefile

RUN make install

CMD ["uvicorn", "--port", "8000","app:app" ]
