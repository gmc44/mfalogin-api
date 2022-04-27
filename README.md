# mfalogin-api
tiny api (python flask) usefull with [gmc44/keycloak-mfalogin-authenticator](https://github.com/gmc44/keycloak-mfalogin-authenticator)
### Proxy Settings
uncomment ENV line in Dockerfile :

`ENV https_proxy http://your.proxy.url:3128`
### Install Docker, Docker-Compose
    dnf update
    export https_proxy="http://your.proxy.url:3128"
    wget -qO- https://get.docker.com/ | sh
    systemctl enable docker.service
    systemctl start docker.service
    curl -L "https://github.com/docker/compose/releases/download/1.25.4/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose

### Start Docker-Compose
    cd mfalogin-api
    docker-compose up -d

### Follow logs
    docker-compose logs -f app

### Open swagger docs
    http://yourip:5000/apidocs/
    
![swagger view](doc/swagger.png?raw=true "swagger view")