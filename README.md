# mfalogin-api
tiny api (python flask) usefull with [gmc44/keycloak-mfalogin-authenticator](https://github.com/gmc44/keycloak-mfalogin-authenticator)
### Proxy Settings
uncomment ENV line in Dockerfile :

`ENV https_proxy http://your.proxy.url:3128`

### Git Clone
`git clone https://github.com/gmc44/mfalogin-api.git`

### Install Docker, Docker-Compose
    dnf|apt update
    export https_proxy="http://your.proxy.url:3128"
    wget -qO- https://get.docker.com/ | sh
    systemctl enable docker.service
    systemctl start docker.service
    #set proxy
    mkdir /etc/systemd/system/docker.service.d
    echo """ [Service]
    Environment="HTTP_PROXY=http://your.proxy.url:3128"
    Environment="HTTPS_PROXY=http://your.proxy.url:3128"
    Environment="NO_PROXY= hostname.example.com,172.10.10.10" """ > /etc/systemd/system/docker.service.d/http-proxy.conf
    systemctl daemon-reload
    systemctl restart docker
    systemctl show docker --property Environment
    #install docker-compose
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