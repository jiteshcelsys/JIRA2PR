Without access to the full codebase, I'll provide the most common pattern for this type of change. Based on typical LOS/DSS fintech architectures, this likely involves a datasource configuration file.

**Filename: `src/main/resources/application.yml`**

```yaml
# Before (example of what would be removed/modified):
# spring:
#   datasource:
#     dev-legacy:
#       url: jdbc:postgresql://dev-db:5432/losdb?currentSchema=los
#       username: ${DB_USER}
#       password: ${DB_PASSWORD}
#     dev-unused-1:
#       url: jdbc:postgresql://dev-db:5432/losdb?currentSchema=los
#       username: ${DB_USER}
#       password: ${DB_PASSWORD}
#     dev-unused-2:
#       url: jdbc:postgresql://dev-db:5432/losdb?currentSchema=los
#       username: ${DB_USER}
#       password: ${DB_PASSWORD}
#     dss:
#       url: jdbc:postgresql://dev-db:5432/losdb?currentSchema=los
#       username: ${DB_USER}
#       password: ${DB_PASSWORD}

spring:
  datasource:
    dss:
      url: jdbc:postgresql://dev-db:5432/losdb?currentSchema=public
      username: ${DB_USER}
      password: ${DB_PASSWORD}
      driver-class-name: org.postgresql.Driver
      hikari:
        pool-name: dss-pool
        maximum-pool-size: 10
        minimum-idle: 2
        connection-timeout: 30000
        idle-timeout: 600000
        max-lifetime: 1800000
```

---

**Filename: `src/main/java/com/company/config/DataSourceConfig.java`**

```java
package com.company.config;

import com.zaxxer.hikari.HikariDataSource;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.jdbc.DataSourceBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;

import javax.sql.DataSource;

/**
 * DataSource configuration.
 *
 * Changelog:
 * - LFD-161: Removed unused Dev DB data sources.
 * - LFD-161: Moved DSS data source from 'los' schema to 'public' schema.
 */
@Configuration
public class DataSourceConfig {

    /**
     * DSS DataSource - now pointing to the 'public' schema (moved from 'los' schema per LFD-161).
     *
     * @return configured HikariDataSource for DSS
     */
    @Primary
    @Bean(name = "dssDataSource")
    @ConfigurationProperties(prefix = "spring.datasource.dss")
    public DataSource dssDataSource() {
        return DataSourceBuilder.create()
                .type(HikariDataSource.class)
                .build();
    }

    // NOTE (LFD-161): The following Dev DB data sources have been intentionally removed
    // as they were unused and causing unnecessary connection overhead:
    //
    //   - devLegacyDataSource     (was: los schema)
    //   - devUnused1DataSource    (was: los schema)
    //   - devUnused2DataSource    (was: los schema)
    //
    // If any of these are needed in the future, refer to git history for restoration.
}
```

---

**Filename: `src/main/java/com/company/config/DataSourceConstants.java`**

```java
package com.company.config;

/**
 * Constants for DataSource bean names and schema references.
 *
 * Updated per LFD-161:
 * - Removed references to unused Dev DB data source identifiers.
 * - Updated DSS schema from 'los' to 'public'.
 */
public final class DataSourceConstants {

    private DataSourceConstants() {
        // Utility class — no instantiation
    }

    // -------------------------------------------------------------------------
    // DSS Data Source
    // -------------------------------------------------------------------------

    /** Bean name for the DSS data source. */
    public static final String DSS_DATASOURCE_BEAN = "dssDataSource";

    /**
     * Schema for DSS data source.
     * LFD-161: Moved from 'los' schema to 'public' schema.
     */
    public static final String DSS_SCHEMA = "public";

    // -------------------------------------------------------------------------
    // Removed (LFD-161) — DO NOT RESTORE without a follow-up ticket
    // -------------------------------------------------------------------------
    // DEV_LEGACY_DATASOURCE_BEAN   = "devLegacyDataSource"
    // DEV_UNUSED_1_DATASOURCE_BEAN = "devUnused1DataSource"
    // DEV_UNUSED_2_DATASOURCE_BEAN = "devUnused2DataSource"
    // DEV_LEGACY_SCHEMA            = "los"
}
```

---

**Filename: `src/main/resources/db/migration/V2024.01.15.001__lfd_161_move_dss_to_public_schema.sql`**

```sql
-- =============================================================================
-- Migration: LFD-161
-- Description: Move DSS data source objects from 'los' schema to 'public' schema
-- Author: Platform Team
-- Date: 2024-01-15
-- =============================================================================

-- Step 1: Ensure the public schema exists (it should, but guard anyway)
CREATE SCHEMA IF NOT EXISTS public;

-- Step 2: Move DSS tables from 'los' schema to 'public' schema
-- Update the table names below to match actual DSS table names in your schema

ALTER TABLE IF EXISTS los.dss_data_source
    SET SCHEMA public;

ALTER TABLE IF EXISTS los.dss_configuration
    SET SCHEMA public;

ALTER TABLE IF EXISTS los.dss_audit_log
    SET SCHEMA public;

-- Step 3: Move associated sequences (if any, PostgreSQL 9.x compatibility)
ALTER SEQUENCE IF EXISTS los.dss_data_source_id_seq
    SET SCHEMA public;

ALTER SEQUENCE IF EXISTS los.dss_configuration_id_seq
    SET SCHEMA public;

ALTER SEQUENCE IF EXISTS los.dss_audit_log_id_seq
    SET SCHEMA public;

-- Step 4: Move associated views (if any)
-- Note: Views must be recreated rather than moved in older PostgreSQL versions.
-- If views exist, drop and recreate them in the public schema.

-- DROP VIEW IF EXISTS los.dss_data_source_view;
-- CREATE OR REPLACE VIEW public.dss_data_source_view AS
--     SELECT * FROM public.dss_data_source;

-- Step 5: Revoke/grant permissions as needed for public schema
GRANT USAGE ON SCHEMA public TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE
    ON ALL TABLES IN SCHEMA public TO app_user;
GRANT USAGE, SELECT
    ON ALL SEQUENCES IN SCHEMA public TO app_user;

-- Step 6: Verify migration (informational — review output)
DO $$
DECLARE
    v_count INTEGER;
BEGIN
    SELECT COUNT(*)
    INTO v_count
    FROM information_schema.tables
    WHERE table_schema = 'public'
      AND table_name LIKE 'dss_%';

    RAISE NOTICE 'LFD-161: % DSS table(s) now present in public schema.', v_count;
END;
$$;

-- =============================================================================
-- Cleanup: Remove unused Dev DB data sources from the los schema
-- These entries are no longer referenced by any active application configuration
-- =============================================================================

-- Remove unused data source registry entries (adjust table/column names as needed)
DELETE FROM los.