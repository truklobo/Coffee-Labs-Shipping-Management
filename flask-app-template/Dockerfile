# start by pulling the python image
FROM python:3.8-alpine

# copy the requirements file into the Docker image
COPY ./requirements.txt /app/requirements.txt

# switch working directory
WORKDIR /app
RUN apk add --update --no-cache --virtual .tmp-build-deps \
    gcc libc-dev linux-headers postgresql-dev \
    && apk add libffi-dev

# install the dependencies and packages in the requirements file
RUN python -m pip install --no-cache-dir --disable-pip-version-check --requirement requirements.txt

# copy every content from the local file to the image
COPY . /app

# configure the container to run in an executed manner
# ENTRYPOINT [ "python" ]

EXPOSE 5005
CMD ["gunicorn", "--config", "gunicorn-cfg.py", "run:app"]
