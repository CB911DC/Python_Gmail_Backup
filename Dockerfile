FROM python:alpine3.7
WORKDIR /usr/src/app
COPY requirements.txt ./
RUN wget "s3.amazonaws.com/aws-cli/awscli-bundle.zip" -O "awscli-bundle.zip" && \
    unzip awscli-bundle.zip && \
    apk add --update groff less python && \
    rm /var/cache/apk/* && \
    ./awscli-bundle/install -i /usr/local/aws -b /usr/local/bin/aws && \
    rm awscli-bundle.zip && \
    rm -rf awscli-bundle && \
    pip install --no-cache-dir -r requirements.txt && \
    apk --no-cache add nano
COPY main.py .
#ENTRYPOINT ["python", "./main.py"]