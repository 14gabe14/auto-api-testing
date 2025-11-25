FROM genomenexus/gn-mongo

ENV API=genome-nexus

USER root

RUN echo "deb http://archive.debian.org/debian stretch main contrib non-free" > /etc/apt/sources.list && \
    apt update && \
    apt install -y default-jdk wget tar python3 && \
    apt -y autoremove

COPY ./apis/genome-nexus/ /api
COPY ./infrastructure/ /infrastructure/

RUN wget https://downloads.mitmproxy.org/6.0.2/mitmproxy-6.0.2-linux.tar.gz && \
    tar -xf mitmproxy-6.0.2-linux.tar.gz

CMD mkdir -m 777 -p /results/$API/$TOOL/$RUN && \
    sh /startup.sh & \
    sh /infrastructure/jacoco/collect-coverage-interval.sh & \
    /mitmdump -p 9090 --mode reverse:http://localhost:8080/ -s /infrastructure/mitmproxy/store-interactions.py & \
    java -javaagent:/infrastructure/jacoco/org.jacoco.agent-0.8.7-runtime.jar=includes=*,output=tcpserver,port=12345,address=* -Dfile.encoding=UTF-8 -Dspring.data.mongodb.uri=mongodb://127.0.0.1:27017/annotator -jar /api/genome-nexus-sut.war