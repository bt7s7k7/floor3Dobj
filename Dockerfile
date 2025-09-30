FROM ubuntu:22.04

# Create program install folder
ENV PROGRAM_PATH /home/floorplan_to_blender
RUN mkdir -p ${PROGRAM_PATH}

# Install required dependencies
RUN apt-get update && \
	apt-get install -y \
	curl \
	bzip2 \
	libfreetype6 \
	libgl1-mesa-dev \
	libglu1-mesa \
	libxi6 \
    libsm6 \
	xz-utils \
	libxrender1 \
    nano \
	dos2unix \
	software-properties-common  && \
	apt-get -y autoremove && \
	rm -rf /var/lib/apt/lists/*

# Add repository for outdated python versions
RUN add-apt-repository ppa:deadsnakes/ppa

# Prevent prompt for timezone
ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

# Install python3.8
RUN apt-get update && \
	apt-get install -y \
	python3.8 python3-pip python3.8-dev python3.8-distutils  && \
	apt-get -y autoremove && \
	rm -rf /var/lib/apt/lists/*
    
# Setup python
RUN python3.8 -m pip install --upgrade pip

# Setup dependencies
COPY ./requirements.txt ${PROGRAM_PATH}/requirements.txt
RUN python3.8 -m pip install --ignore-installed -r ${PROGRAM_PATH}/requirements.txt

# Add our program
COPY ./FloorplanToBlenderLib ${PROGRAM_PATH}/FloorplanToBlenderLib
COPY ./Images ${PROGRAM_PATH}/Images
COPY ./Configs ${PROGRAM_PATH}/Configs
COPY ./create_glb.py ${PROGRAM_PATH}/create_glb.py
COPY ./create_glb_api.py ${PROGRAM_PATH}/create_glb_api.py
    
# Server ports
EXPOSE 8081

WORKDIR ${PROGRAM_PATH}
ENTRYPOINT python3.8 create_glb_api.py
