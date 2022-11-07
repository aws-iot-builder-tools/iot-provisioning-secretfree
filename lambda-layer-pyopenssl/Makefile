P := $(shell pwd)


default: build-pyOpensslLayer

build-pyOpensslLayer:
	docker run \
		-v "${P}":/var/task  -u $(shell id -u) \
		lambci/lambda:build-python3.6 /bin/bash \
		-c "mkdir -p python && pip install pyOpenSSL==19.0.0 -t python/; exit"
#	zip -r ${P}/lambda-layer-pyopenssl.zip python/

