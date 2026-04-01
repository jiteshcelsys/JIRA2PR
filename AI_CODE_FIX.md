Based on common Spring Boot multi-datasource configuration patterns:

**filename: `src/main/resources/application-dev.yml`**
```yaml
spring:
  datasource:
    # Primary/Default datasource (public schema)
    url: jdbc:postgresql://${DB_HOST:localhost}:${DB_PORT:5432}/${DB_NAME:lfd_db}
    username: ${DB_USERNAME:postgres}
    password: ${DB_PASSWORD:postgres}
    driver-class-name: org.postgresql.Driver
    hikari:
      schema: public
      pool-name: primary-pool
      maximum-pool-size: 10

  # DSS datasource moved from 'los' schema to 'public' schema
  dss-datasource:
    url: jdbc:postgresql://${DB_HOST:localhost}:${DB_PORT:5432}/${DB_NAME:lfd_db}
    username: ${DB_USERNAME:postgres}
    password: ${DB_PASSWORD:postgres}
    driver-class-name: org.postgresql.Driver
    hikari:
      schema: public        # Previously: los
      pool-name: dss-pool
      maximum-pool-size: 5

  # REMOVED: Unused Dev DB data sources (previously listed below)
  # legacy-datasource:   REMOVED - unused
  # test-datasource:     REMOVED - unused
  # staging-datasource:  REMOVED - unused
```

---

**filename: `src/main/kotlin/com/lfd/config/DataSourceConfig.kt`**
```kotlin
package com.lfd.config

import com.zaxxer.hikari.HikariDataSource
import org.springframework.boot.context.properties.ConfigurationProperties
import org.springframework.boot.jdbc.DataSourceBuilder
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.context.annotation.Primary
import org.springframework.context.annotation.Profile
import javax.sql.DataSource

@Configuration
class DataSourceConfig {

    /**
     * Primary data source using the public schema.
     */
    @Primary
    @Bean(name = ["primaryDataSource"])
    @ConfigurationProperties(prefix = "spring.datasource")
    fun primaryDataSource(): DataSource {
        return DataSourceBuilder.create().type(HikariDataSource::class.java).build()
    }

    /**
     * DSS data source — moved from 'los' schema to 'public' schema.
     * See: LFD-161
     */
    @Bean(name = ["dssDataSource"])
    @ConfigurationProperties(prefix = "spring.dss-datasource")
    fun dssDataSource(): DataSource {
        return DataSourceBuilder.create().type(HikariDataSource::class.java).build()
    }

    // REMOVED: legacyDataSource     — unused Dev DB data source (LFD-161)
    // REMOVED: testDataSource        — unused Dev DB data source (LFD-161)
    // REMOVED: stagingDataSource     — unused Dev DB data source (LFD-161)
}
```

---

**filename: `src/main/kotlin/com/lfd/config/DssJpaConfig.kt`**
```kotlin
package com.lfd.config

import org.springframework.beans.factory.annotation.Qualifier
import org.springframework.boot.orm.jpa.EntityManagerFactoryBuilder
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.data.jpa.repository.config.EnableJpaRepositories
import org.springframework.orm.jpa.JpaTransactionManager
import org.springframework.orm.jpa.LocalContainerEntityManagerFactoryBean
import org.springframework.transaction.PlatformTransactionManager
import org.springframework.transaction.annotation.EnableTransactionManagement
import javax.sql.DataSource

@Configuration
@EnableTransactionManagement
@EnableJpaRepositories(
    basePackages = ["com.lfd.dss.repository"],
    entityManagerFactoryRef = "dssEntityManagerFactory",
    transactionManagerRef = "dssTransactionManager"
)
class DssJpaConfig {

    /**
     * Entity manager factory for DSS repositories.
     * Schema updated from 'los' to 'public' as part of LFD-161.
     */
    @Bean(name = ["dssEntityManagerFactory"])
    fun dssEntityManagerFactory(
        builder: EntityManagerFactoryBuilder,
        @Qualifier("dssDataSource") dssDataSource: DataSource
    ): LocalContainerEntityManagerFactoryBean {
        return builder
            .dataSource(dssDataSource)
            .packages("com.lfd.dss.model")
            .persistenceUnit("dss")
            .properties(
                mapOf(
                    "hibernate.default_schema" to "public",  // Previously: "los"
                    "hibernate.hbm2ddl.auto" to "validate",
                    "hibernate.dialect" to "org.hibernate.dialect.PostgreSQLDialect"
                )
            )
            .build()
    }

    @Bean(name = ["dssTransactionManager"])
    fun dssTransactionManager(
        @Qualifier("dssEntityManagerFactory")
        dssEntityManagerFactory: org.springframework.orm.jpa.LocalContainerEntityManagerFactoryBean
    ): PlatformTransactionManager {
        return JpaTransactionManager(
            dssEntityManagerFactory.`object`
                ?: throw IllegalStateException("DSS EntityManagerFactory failed to initialize")
        )
    }
}
```

---

**filename: `src/main/resources/db/migration/V202401151200__move_dss_to_public_schema.sql`**
```sql
-- ============================================================
-- Migration: LFD-161
-- Move DSS data source objects from 'los' schema to 'public'
-- schema, and clean up unused dev data source references.
-- ============================================================

-- Step 1: Ensure public schema exists (idempotent)
CREATE SCHEMA IF NOT EXISTS public;

-- Step 2: Move DSS tables from 'los' schema to 'public' schema
-- NOTE: Update the table names below to match actual DSS tables.

ALTER TABLE IF EXISTS los.dss_connection       SET SCHEMA public;
ALTER TABLE IF EXISTS los.dss_configuration    SET SCHEMA public;
ALTER TABLE IF EXISTS los.dss_metadata         SET SCHEMA public;
ALTER TABLE IF EXISTS los.dss_audit_log        SET SCHEMA public;

-- Step 3: Move DSS sequences (if any)
ALTER SEQUENCE IF EXISTS los.dss_connection_id_seq       SET SCHEMA public;
ALTER SEQUENCE IF EXISTS los.dss_configuration_id_seq    SET SCHEMA public;
ALTER SEQUENCE IF EXISTS los.dss_metadata_id_seq         SET SCHEMA public;
ALTER SEQUENCE IF EXISTS los.dss_audit_log_id_seq        SET SCHEMA public;

-- Step 4: Move DSS views (if any)
-- Views must be recreated; drop from 'los' and recreate in 'public'
DROP VIEW IF EXISTS los.dss_connection_view;
CREATE OR REPLACE VIEW public.dss_connection_view AS
    SELECT * FROM public.dss_connection;

-- Step 5: Update search_path or schema references in DSS functions (if any)
-- ALTER FUNCTION los.some_dss_function() SET SCHEMA public;

-- Step 6: Drop the 'los' schema if it is now empty and no longer needed
-- WARNING: Only run this if 'los' schema has NO other objects.
-- DO $$
-- BEGIN
--     IF NOT EXISTS (
--         SELECT 1 FROM information_schema.tables
--         WHERE table_schema = 'los'
--     ) THEN
--         DROP SCHEMA los;
--     END IF;
-- END $$;

-- Step 7: Verify migration
DO $$
DECLARE