FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8 LC_ALL=C.UTF-8
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl gnupg lsb-release \
    && curl --retry 3 -fsSL https://packages.osrfoundation.org/gazebo.gpg -o /usr/share/keyrings/gazebo.gpg \
    && echo 'deb [signed-by=/usr/share/keyrings/gazebo.gpg] https://packages.osrfoundation.org/gazebo/ubuntu-stable jammy main' > /etc/apt/sources.list.d/gazebo.list \
    && apt-get update && apt-get install -y --no-install-recommends \
       gz-harmonic build-essential cmake ninja-build ccache git python3 python3-dev python3-pip python3-venv \
       libeigen3-dev libopencv-dev libxml2-dev libxml2-utils libssl-dev libunwind-dev \
       protobuf-compiler pkg-config libgstreamer-plugins-base1.0-dev \
       gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad \
       gstreamer1.0-plugins-ugly gstreamer1.0-libav zip unzip rsync bc \
       libgl1-mesa-dri mesa-utils procps iproute2 xauth \
    && apt-get clean
ENV QT_X11_NO_MITSHM=1
WORKDIR /workspace
CMD ["bash"]
