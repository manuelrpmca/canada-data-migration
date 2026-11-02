{#-
    Use the custom schema name as is (staging, marts, reference) instead of dbt's default
    "<target schema>_<custom schema>". The warehouse has one environment per file, so the
    prefix would add nothing.
-#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
