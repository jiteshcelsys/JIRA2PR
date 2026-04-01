### File 1: `src/main/resources/application-dev.yml`

```yaml
# application-dev.yml
# LFD-161: Removed unused Dev DB data sources; DSS now points to public schema

spring:
  datasource:
    # Primary LOS data source
    los:
      url: jdbc:postgresql://${DB_HOST:localhost}:${DB_PORT:5432}/${DB_NAME:losdb}
      username: ${DB_USERNAME:losuser}
      password: ${DB_PASSWORD:lospassword}
      driver-class-name: org.postgresql.Driver
      hikari:
        schema: los
        pool-name: LOS-Pool
        maximum-pool-size: 10
        minimum-idle: 2

    # DSS data source — moved from 'los' schema to 'public' schema (LFD-161)
    dss:
      url: jdbc:postgresql://${DB_HOST:localhost}:${DB_PORT:5432}/${DB_NAME:losdb}
      username: ${DB_USERNAME:losuser}
      password: ${DB_PASSWORD:lospassword}
      driver-class-name: org.postgresql.Driver
      hikari:
        schema: public
        pool-name: DSS-Pool
        maximum-pool-size: 10
        minimum-idle: 2

    # REMOVED (LFD-161) — the following unused Dev data sources have been cleaned up:
    # - legacy-reporting
    # - dev-analytics
    # - temp-integration
```

---

### File 2: `src/main/java/com/company/lfd/config/DataSourceConfig.java`

```java
package com.company.lfd.config;

import com.zaxxer.hikari.HikariDataSource;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.jdbc.DataSourceBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;

import javax.sql.DataSource;

/**
 * DataSourceConfig
 *
 * LFD-161:
 * - Removed unused Dev DB data sources (legacy-reporting, dev-analytics, temp-integration).
 * - Moved DSS data source configuration from 'los' schema to 'public' schema.
 */
@Configuration
public class DataSourceConfig {

    /**
     * Primary LOS data source bound to the 'los' schema.
     */
    @Primary
    @Bean(name = "losDataSource")
    @ConfigurationProperties(prefix = "spring.datasource.los")
    public DataSource losDataSource() {
        return DataSourceBuilder.create()
                .type(HikariDataSource.class)
                .build();
    }

    /**
     * DSS data source — now bound to the 'public' schema.
     * Previously configured under the 'los' schema; moved as part of LFD-161.
     */
    @Bean(name = "dssDataSource")
    @ConfigurationProperties(prefix = "spring.datasource.dss")
    public DataSource dssDataSource() {
        return DataSourceBuilder.create()
                .type(HikariDataSource.class)
                .build();
    }

    // -------------------------------------------------------------------------
    // REMOVED as part of LFD-161 — unused Dev DB data sources:
    //
    // @Bean(name = "legacyReportingDataSource")
    // @ConfigurationProperties(prefix = "spring.datasource.legacy-reporting")
    // public DataSource legacyReportingDataSource() { ... }
    //
    // @Bean(name = "devAnalyticsDataSource")
    // @ConfigurationProperties(prefix = "spring.datasource.dev-analytics")
    // public DataSource devAnalyticsDataSource() { ... }
    //
    // @Bean(name = "tempIntegrationDataSource")
    // @ConfigurationProperties(prefix = "spring.datasource.temp-integration")
    // public DataSource tempIntegrationDataSource() { ... }
    // -------------------------------------------------------------------------
}
```

---

### File 3: `src/main/resources/db/migration/V20240101120000__lfd161_move_dss_to_public_schema.sql`

```sql
-- =============================================================================
-- Migration: V20240101120000__lfd161_move_dss_to_public_schema.sql
-- Ticket:    LFD-161
-- Summary:   Move DSS data source objects from the 'los' schema to the
--            'public' schema. Drop unused Dev DB data source artifacts.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- STEP 1: Move DSS tables from 'los' schema to 'public' schema
-- -----------------------------------------------------------------------------

-- Transfer dss_source table
ALTER TABLE IF EXISTS los.dss_source
    SET SCHEMA public;

-- Transfer dss_configuration table
ALTER TABLE IF EXISTS los.dss_configuration
    SET SCHEMA public;

-- Transfer dss_audit_log table
ALTER TABLE IF EXISTS los.dss_audit_log
    SET SCHEMA public;

-- Transfer any DSS-related views
ALTER VIEW IF EXISTS los.vw_dss_summary
    SET SCHEMA public;

-- Transfer any DSS-related sequences
ALTER SEQUENCE IF EXISTS los.dss_source_id_seq
    SET SCHEMA public;

ALTER SEQUENCE IF EXISTS los.dss_configuration_id_seq
    SET SCHEMA public;

-- -----------------------------------------------------------------------------
-- STEP 2: Update any foreign key constraints referencing los.dss_* objects
--         (constraints are automatically updated when schema is changed,
--          but cross-schema references must be verified manually)
-- -----------------------------------------------------------------------------

-- Verify no remaining references to los.dss_* exist after migration
DO $$
DECLARE
    v_count INTEGER;
BEGIN
    SELECT COUNT(*)
    INTO v_count
    FROM information_schema.tables
    WHERE table_schema = 'los'
      AND table_name LIKE 'dss%';

    IF v_count > 0 THEN
        RAISE WARNING 'LFD-161: % DSS table(s) still remain in the los schema. Manual review required.', v_count;
    ELSE
        RAISE NOTICE 'LFD-161: All DSS tables successfully moved to public schema.';
    END IF;
END;
$$;

-- -----------------------------------------------------------------------------
-- STEP 3: Clean up unused Dev DB data source artifacts
-- -----------------------------------------------------------------------------

-- Drop legacy-reporting schema objects (unused Dev data source)
DROP TABLE IF EXISTS public.legacy_reporting_source CASCADE;
DROP TABLE IF EXISTS public.legacy_reporting_config CASCADE;
DROP VIEW  IF EXISTS public.vw_legacy_reporting CASCADE;

-- Drop dev-analytics schema objects (unused Dev data source)
DROP TABLE IF EXISTS public.dev_analytics_source CASCADE;
DROP TABLE IF EXISTS public.dev_analytics_config CASCADE;
DROP VIEW  IF EXISTS public.vw_dev_analytics CASCADE;

-- Drop temp-integration schema objects (unused Dev data source)
DROP TABLE IF EXISTS public.temp_integration_source CASCADE;
DROP TABLE IF EXISTS public.temp_integration_config CASCADE;

-- -----------------------------------------------------------------------------
-- STEP 4: Revoke any grants previously scoped to los schema for DSS objects
--         and re-apply to public schema
-- -----------------------------------------------------------------------------

-- Re-grant permissions on moved DSS objects (adjust role names as needed)
GRANT SELECT, INSERT, UPDATE, DELETE ON public.dss_source        TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.dss_configuration  TO app_user;
GRANT SELECT                          ON public.dss_audit_log      TO app_user;
GRANT SELECT                          ON public.vw_dss_summary     TO app_user;

GRANT USAGE, SELECT ON SEQUENCE public.dss_source_id_seq        TO app_user;
GRANT USAGE, SELECT ON SEQUENCE public.dss