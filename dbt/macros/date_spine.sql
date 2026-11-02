{#-
    One row per calendar day from start_date to end_date, both inclusive, in a column named
    date_day. The arguments are SQL expressions that return a DATE.

    Adapter-specific SQL lives here so the models stay portable (ADR 0007). BigQuery gets its
    implementation with the bigquery target in M5.
-#}
{% macro date_spine(start_date, end_date) -%}
    {{ return(adapter.dispatch('date_spine', 'cdm')(start_date, end_date)) }}
{%- endmacro %}

{% macro duckdb__date_spine(start_date, end_date) -%}
    select cast(range as date) as date_day
    from range(
        cast(({{ start_date }}) as timestamp),
        cast(({{ end_date }}) as timestamp) + interval 1 day,
        interval 1 day
    )
{%- endmacro %}

{% macro default__date_spine(start_date, end_date) -%}
    {{ exceptions.raise_compiler_error(
        "date_spine has no implementation for adapter '" ~ target.type ~ "' yet (planned for M5)."
    ) }}
{%- endmacro %}
