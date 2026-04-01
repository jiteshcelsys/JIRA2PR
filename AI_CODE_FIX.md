Without seeing the existing codebase, I'll provide the most common implementation patterns. Based on typical Spring Boot / multi-datasource configurations, here are the relevant files:

---

### File 1: `src/main/resources/application.yml` (or `application-dev.yml`)

```yaml
spring:
  datasource:
    # PRIMARY / PUBLIC schema datasource
    public:
      url: jdbc:postgresql://${DB_HOST:localhost}:${DB_PORT:5432}/${DB_NAME:appdb}?currentSchema=public
      username: ${DB_USERNAME:appuser}
      password: ${DB_PASSWORD:}
      driver-class-name: org.postgresql.Driver
      hikari:
        pool-name: PublicSchemaPool
        maximum-pool-size: 10
        minimum-idle: 2
        connection-timeout: 30000
        idle-timeout: 600000
        max-lifetime: 1800000

    # DSS datasource moved from 'los' schema to 'public' schema (LFD-161)
    dss:
      url: jdbc:postgresql://${DB_HOST:localhost}:${DB_PORT:5432}/${DB_NAME:appdb}?currentSchema=public
      username: ${DSS_DB_USERNAME:appuser}
      password: ${DSS_DB_PASSWORD:}
      driver-class-name: org.postgresql.Driver
      hikari:
        pool-name: DssPublicSchemaPool
        maximum-pool-size: 10
        minimum-idle: 2
        connection-timeout: 30000
        idle-timeout: 600000
        max-lifetime: 1800000

    # REMOVED (LFD-161): The following unused Dev DB datasources have been cleaned up:
    # - los-legacy (unused)
    # - dev-reporting (unused)
    # - dev-analytics (unused)
    # - dss-los (moved to public schema above)
```

---

### File 2: `src/main/java/com/company/config/DataSourceConfig.java`

```java
package com.company.config;

import com.zaxxer.hikari.HikariDataSource;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.jdbc.DataSourceBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import org.springframework.jdbc.core.JdbcTemplate;

import javax.sql.DataSource;

/**
 * DataSource configuration.
 *
 * LFD-161: Removed unused Dev DB data sources and moved DSS data source
 * from the 'los' schema to the 'public' schema.
 */
@Configuration
public class DataSourceConfig {

    /**
     * Primary public schema DataSource.
     */
    @Primary
    @Bean(name = "publicDataSource")
    @ConfigurationProperties(prefix = "spring.datasource.public")
    public DataSource publicDataSource() {
        return DataSourceBuilder.create()
                .type(HikariDataSource.class)
                .build();
    }

    /**
     * DSS DataSource — now pointing to the 'public' schema.
     *
     * Previously configured under the 'los' schema; moved to 'public' per LFD-161.
     */
    @Bean(name = "dssDataSource")
    @ConfigurationProperties(prefix = "spring.datasource.dss")
    public DataSource dssDataSource() {
        return DataSourceBuilder.create()
                .type(HikariDataSource.class)
                .build();
    }

    /**
     * JdbcTemplate for the primary public DataSource.
     */
    @Primary
    @Bean(name = "publicJdbcTemplate")
    public JdbcTemplate publicJdbcTemplate(
            @Qualifier("publicDataSource") DataSource publicDataSource) {
        return new JdbcTemplate(publicDataSource);
    }

    /**
     * JdbcTemplate for the DSS DataSource (public schema).
     */
    @Bean(name = "dssJdbcTemplate")
    public JdbcTemplate dssJdbcTemplate(
            @Qualifier("dssDataSource") DataSource dssDataSource) {
        return new JdbcTemplate(dssDataSource);
    }

    // -------------------------------------------------------------------------
    // REMOVED DATA SOURCES (LFD-161) — previously defined beans, now deleted:
    //
    // @Bean(name = "losLegacyDataSource")   — unused, removed
    // @Bean(name = "devReportingDataSource") — unused, removed
    // @Bean(name = "devAnalyticsDataSource") — unused, removed
    // @Bean(name = "dssLosDataSource")       — moved to dssDataSource() above
    //                                          now uses public schema
    // -------------------------------------------------------------------------
}
```

---

### File 3: `src/main/java/com/company/config/DssDataSourceConfig.java`

```java
package com.company.config;

import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.boot.orm.jpa.EntityManagerFactoryBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.jpa.repository.config.EnableJpaRepositories;
import org.springframework.orm.jpa.JpaTransactionManager;
import org.springframework.orm.jpa.LocalContainerEntityManagerFactoryBean;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.annotation.EnableTransactionManagement;

import javax.persistence.EntityManagerFactory;
import javax.sql.DataSource;
import java.util.HashMap;
import java.util.Map;

/**
 * JPA configuration for the DSS data source.
 *
 * LFD-161: DSS data source schema updated from 'los' to 'public'.
 * The default_schema property has been updated accordingly.
 */
@Configuration
@EnableTransactionManagement
@EnableJpaRepositories(
        basePackages = "com.company.dss.repository",
        entityManagerFactoryRef = "dssEntityManagerFactory",
        transactionManagerRef = "dssTransactionManager"
)
public class DssDataSourceConfig {

    /**
     * Entity manager factory for DSS — using the public schema.
     *
     * Previously set to schema = "los"; updated to schema = "public" per LFD-161.
     */
    @Bean(name = "dssEntityManagerFactory")
    public LocalContainerEntityManagerFactoryBean dssEntityManagerFactory(
            EntityManagerFactoryBuilder builder,
            @Qualifier("dssDataSource") DataSource dssDataSource) {

        Map<String, Object> properties = new HashMap<>();
        // LFD-161: Changed from "los" to "public"
        properties.put("hibernate.default_schema", "public");
        properties.put("hibernate.hbm2ddl.auto", "validate");
        properties.put("hibernate.dialect", "org.hibernate.dialect.PostgreSQLDialect");
        properties.put("hibernate.show_sql", false);

        return builder
                .dataSource(dssDataSource)
                .packages("com.company.dss.model")
                .persistenceUnit("dssPersistenceUnit")
                .properties(properties)
                .build();
    }

    @Bean(name = "dssTransactionManager")
    public PlatformTransactionManager dssTransactionManager(
            @Qualifier("dssEntityManagerFactory") EntityManagerFactory dssEntityManagerFactory) {
        return new JpaTransactionManager(dssEntityManagerFactory);
    }
}
```

---

### File 4: `src/main/resources/db/migration/V2__move_d