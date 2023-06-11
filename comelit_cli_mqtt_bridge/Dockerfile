ARG BUILD_FROM
FROM $BUILD_FROM

WORKDIR /app

RUN apk add --no-cache --update nodejs npm

COPY src/package.json /app/package.json
COPY src/package-lock.json /app/package-lock.json
RUN npm ci

COPY ./src /app

RUN chmod a+x /app/run.sh

CMD [ "./run.sh" ]
