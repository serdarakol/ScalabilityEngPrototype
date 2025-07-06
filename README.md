# ScalabilityEngPrototype
scalability engineering prototype project

dependency
minikube and docker

if you want to change the species seed data run below command to generate new species seed before building and deploying the application

```shell
python3 src/data_generator/script.py --seed 42 --count 100 --output src/server/species_seed.json
```


```shell
minikube delete
```

```shell
minikube start
```

Make sure images are build within Minikube:

```shell
eval "$(minikube -p minikube docker-env)"
```

```shell
docker compose build
```

Check that the images are correctly tagged with
```shell
docker image ls
```

It should look like this:
```
REPOSITORY                                TAG        IMAGE ID       CREATED              SIZE
sca-en-prototype/species-service           latest     b61567252a8b   About a minute ago   413MB
registry.k8s.io/kube-apiserver            v1.32.0    2b5bd0f16085   6 months ago         93.9MB
registry.k8s.io/kube-controller-manager   v1.32.0    a8d049396f6b   6 months ago         87.2MB
registry.k8s.io/kube-scheduler            v1.32.0    c3ff26fb59f3   6 months ago         67.9MB
registry.k8s.io/kube-proxy                v1.32.0    2f50386e20bf   6 months ago         97.1MB
registry.k8s.io/etcd                      3.5.16-0   7fc9d4aa817a   9 months ago         142MB
registry.k8s.io/coredns/coredns           v1.11.3    2f6c962e7b83   11 months ago        60.2MB
registry.k8s.io/pause                     3.10       afb61768ce38   13 months ago        514kB
gcr.io/k8s-minikube/storage-provisioner   v5         ba04bb24b957   4 years ago          29MB
```

Then create the kubernetes deployment:

```shell
kubectl create -f src/k8s/architecture.yaml -n prototype
```

```shell
minikube service species-svc -n prototype --url
```

this will prompt the local url that is routing to the minkube species-svc

eg:
```shell
minikube service species-svc -n prototype --url

http://127.0.0.1:50740
❗  Because you are using a Docker driver on darwin, the terminal needs to be open to run it.

```

important!: use the above url start client side
you can start different client processes on different terminals as much as you want

```shell
cd src/client
npm i

CLIENT_NAME=client-1 THREADS=10 RATE=50 \
SPECIES_IDS=1,2,3,4 SERVER_URL=http://127.0.0.1:50740 \
node load_generator.js
```

collect the data there

apply visualization

apply horizantal scaling

```shell
chmod +x src/scaler/script.sh
```

```shell
 ./src/scaler/script.sh --memory 512Mi --restart
```

```shell
 ./src/scaler/script.sh --cpu 300m --restart
```


```shell
 ./src/scaler/script.sh --replicas 2 --restart
```



then run the scaler with some configurations to apply
do the client run again  collect the data and apply visualizer
(maybe show how it got more avaible since it could serve more and there is less 429 responses)

end the slides





