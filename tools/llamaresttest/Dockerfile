FROM ubuntu:22.04

ENV TOOL=llamaresttest
ENV DEBIAN_FRONTEND=noninteractive

RUN mkdir /tool && \
    mkdir /results && \
    mkdir /specifications

# Install dependencies
RUN apt update && \
    apt -y upgrade && \
    apt -y install python3 python3-pip curl wget && \
    apt -y autoremove

# Copy tool files
COPY ./tool/llama/ /tool/llama/
COPY ./specs/swagger/ /specifications/
COPY ./llamarest.py /tool/
COPY ./requirements.txt /tool/
COPY ./models/ /tool/models/

# Install Python dependencies
WORKDIR /tool
RUN pip3 install --no-cache-dir -r requirements.txt

# Install llama-cpp-python
RUN pip3 install --no-cache-dir llama-cpp-python

CMD mkdir -p /results/$API/$TOOL/$RUN && \
    cd /tool/llama/$API && \
    end=$((SECONDS+600)) && \
    while [ $SECONDS -lt $end ]; do \
        python3 /tool/llamarest.py /specifications/$API.yaml http://localhost:${PORT}/api || true; \
    done && \
    echo "Tool execution completed" > /results/$API/$TOOL/$RUN/completed.txt

