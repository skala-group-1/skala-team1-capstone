# 빌드 컨텍스트 = 저장소 루트 (Flyway 가 data/mock/out 의 schema·seed 를 패키징하므로)
#   docker compose build backend
FROM eclipse-temurin:21-jdk AS build
WORKDIR /src/backend
COPY backend/gradlew backend/settings.gradle backend/build.gradle ./
COPY backend/gradle ./gradle
RUN ./gradlew --no-daemon -q dependencies > /dev/null
COPY data/mock/out /src/data/mock/out
COPY backend/src ./src
RUN ./gradlew --no-daemon bootJar -x test

FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build /src/backend/build/libs/*.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
