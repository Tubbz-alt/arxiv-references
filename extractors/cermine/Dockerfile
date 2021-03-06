FROM python:3.6

ENV VERSION "1.12"
LABEL cermine.version $VERSION

RUN apt-get update && apt-get install -y \
    ca-certificates \
    wget \
    default-jdk \
    gcc \
 && rm -rf /var/lib/apt/lists/*

RUN pip install uwsgi

RUN mkdir /opt/cermine
RUN mkdir /tmp/uploads
RUN wget http://maven.ceon.pl/artifactory/simple/kdd-releases/pl/edu/icm/cermine/cermine-impl/${VERSION}/cermine-impl-${VERSION}-jar-with-dependencies.jar
RUN cp cermine-impl-${VERSION}-jar-with-dependencies.jar /opt/cermine/cermine-impl.jar

ADD requirements.txt /opt/cermine/
RUN pip install -U pip
RUN pip install -r /opt/cermine/requirements.txt
RUN pip install arxiv-base pytz

ADD wsgi.py /opt/cermine/

ENV PATH "/opt/cermine:${PATH}"
ENV LOGLEVEL 20

WORKDIR /opt/cermine/

ADD extract /opt/cermine/extract/

EXPOSE 8000

CMD uwsgi --http-socket :8000 -w wsgi -t 3000 --processes 4 --threads 1 -M --async 100 --ugreen --vacuum
