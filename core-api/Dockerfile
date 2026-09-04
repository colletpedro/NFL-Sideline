# ---- Stage 1: Build ----
FROM maven:3.9-eclipse-temurin-21 AS build

WORKDIR /app

# Download dependencies first (better layer caching)
COPY pom.xml .
RUN mvn -q dependency:go-offline

COPY src ./src
RUN mvn clean package -DskipTests

# ---- Stage 2: Run ----
FROM eclipse-temurin:21-jre-alpine

WORKDIR /app

EXPOSE 8080

COPY --from=build /app/target/*.jar app.jar

ENTRYPOINT ["java", "-jar", "app.jar"]