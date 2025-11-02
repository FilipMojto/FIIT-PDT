# PDT Assignment 2

## Task 1

To be able to import the data, we took the following approach:

1. Install Postgis extension from the link: [postgis](https://postgis.net/documentation/getting_started/install_windows/released_versions/)
2. Enable these extension in Pgadmin: postgis, hstore
    
    CREATE EXTENSION postgis;
    CREATE EXTENSION hstore;
    
3. Download osm2pgsql, a widely used OSM data importer, from the link: [osm2psql](https://osm2pgsql.org/doc/install.html)
4. Add path to osm2pgsql.exe to your environment variables.
5. Import the data by executing the following command:

    
    C:\Users\fmojt\Desktop\pdt_assigment_3>osm2pgsql -d <db_name> -U <db_username> -H <db_localhost> -W --create --slim --hstore --latlong --style <style_file_path> <data_file_path>
    

We verified the installation:

Assignment_4=# \dt
                  List of tables
 Schema |         Name         | Type  |  Owner
--------+----------------------+-------+----------
 public | osm2pgsql_properties | table | postgres
 public | planet_osm_line      | table | postgres
 public | planet_osm_nodes     | table | postgres
 public | planet_osm_point     | table | postgres
 public | planet_osm_polygon   | table | postgres
 public | planet_osm_rels      | table | postgres
 public | planet_osm_roads     | table | postgres
 public | planet_osm_ways      | table | postgres
 public | spatial_ref_sys      | table | postgres
(9 rows)

### SQL Query
```sql
SELECT
    name,
    ST_AsText(ST_Centroid(way)) AS centroid,
    way
FROM planet_osm_polygon
WHERE boundary = 'administrative'
  AND admin_level = '4'
  AND name IS NOT NULL;
```

### Description
This query selects all **administrative boundaries** at level 4 from the `planet_osm_polygon` table, which represent **Slovak regions**.  
The function `ST_Centroid(way)` calculates the **geometric center** of each region's polygon, and `ST_AsText` converts it to a readable text format.

### Purpose
We applied this query to **extract and visualize Slovak regional boundaries** from OpenStreetMap data stored in a PostGIS database.  
By including centroids, each region can be easily labeled or used for further spatial analysis.

### Results
The visualization below shows the **geographic representation of Slovak regions** based on the extracted data.

![Task 2 - Geographic representation of Slovak Regions](img/task_2_geographic_results.png)


