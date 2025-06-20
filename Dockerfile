FROM node:18

# Install Python and required build dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip3 install --upgrade pip

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install Node.js dependencies
RUN npm install

# Install Python dependencies one by one to better handle errors
RUN pip3 install --no-cache-dir pytube
RUN pip3 install --no-cache-dir yt-dlp

# Copy application files
COPY . .

# Expose port
EXPOSE 3000

# Start the application
CMD ["node", "server.js"] 