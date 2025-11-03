## Task 13

### SQL Query

```sql
DROP TABLE IF EXISTS bratislava_buffer;
CREATE TABLE bratislava_buffer AS
SELECT ST_Transform(ST_Buffer(ST_Transform(cb.way, 5514), 20000), 5514) AS buffer
FROM planet_osm_polygon cb
WHERE cb.boundary = 'administrative'
  AND cb.admin_level = '6'
  AND cb.name ILIKE 'bratislava';

SELECT count(*) FROM slovakia_5514;

-- Slovakia polygon in 5514
DROP TABLE IF EXISTS slovakia_5514;
CREATE TABLE slovakia_5514 AS
SELECT ST_Transform(cb.way, 5514) AS geom
FROM planet_osm_polygon cb
WHERE cb.admin_level = '2' AND cb.name ILIKE 'slovensk%';

-- Clipping buffer to Slovakia
DROP TABLE IF EXISTS bratislava_buffer_clipped;
CREATE TABLE bratislava_buffer_clipped AS
SELECT ST_Intersection(bb.buffer, s.geom) AS buffer
FROM bratislava_buffer bb
CROSS JOIN slovakia_5514 s;

-- Uniting Bratislava districts
DROP TABLE IF EXISTS bratislava_districts_union;
CREATE TABLE bratislava_districts_union AS
SELECT ST_Union(ST_Transform(cb.way, 5514)) AS geom
FROM planet_osm_polygon cb
WHERE cb.boundary = 'administrative'
  AND cb.admin_level = '8'
  AND cb.name IN ('okres Bratislava I', 'okres Bratislava II', 
                  'okres Bratislava III', 'okres Bratislava IV', 'okres Bratislava V');

-- Excluding the districts from the buffer
DROP TABLE IF EXISTS bratislava_district_buffer;
CREATE TABLE bratislava_district_buffer AS
SELECT ST_Difference(bb.buffer, bd.geom) AS buffer
FROM bratislava_buffer_clipped bb
CROSS JOIN bratislava_districts_union bd;

-- Viewing result
SELECT * FROM bratislava_district_buffer;

-- Calculating the area
SELECT SUM(ST_Area(buffer)) AS vymera_m2
FROM bratislava_district_buffer;
```

### Interpretation

This query calculates the area of a 20 km buffer zone around Bratislava, excluding the city's own districts and clipped to Slovakia's borders. The analysis follows a multi-stage geometric processing workflow:

**1. Initial Buffer Creation (`bratislava_buffer`)**

A 20 km (20,000 meter) buffer zone is created around the Bratislava administrative boundary (admin_level = '6'). The geometry is transformed to EPSG:5514 (S-JTSK) before buffering to ensure accurate metric distance calculations, then kept in this coordinate system for subsequent operations. This buffer extends 20 km in all directions from Bratislava's boundaries.

**2. Slovakia Boundary Extraction (`slovakia_5514`)**

The national boundary of Slovakia is extracted and transformed to EPSG:5514. This polygon (admin_level = '2') serves as a clipping mask to ensure the buffer zone doesn't extend beyond Slovakia's borders into neighboring countries (Austria, Czech Republic, Hungary).

**3. Buffer Clipping (`bratislava_buffer_clipped`)**

Using `ST_Intersection()`, the buffer is clipped to Slovakia's national boundaries. This operation removes any portions of the buffer that would extend into neighboring countries, ensuring the analysis focuses solely on Slovak territory within 20 km of Bratislava.

**4. Bratislava Districts Union (`bratislava_districts_union`)**

All five Bratislava city districts (admin_level = '8': Bratislava I through V) are merged into a single unified polygon using `ST_Union()`. This creates a complete representation of the city proper that needs to be excluded from the final buffer zone.

**5. Final Buffer Calculation (`bratislava_district_buffer`)**

The `ST_Difference()` function subtracts the unified Bratislava districts from the clipped buffer, creating a "donut" shape that represents only the surrounding area within 20 km of the city, excluding the city itself. This isolates the peripheral zone of interest.

**6. Area Calculation**

Finally, `ST_Area()` computes the total area of this peripheral buffer zone in square meters. Since all operations were performed in EPSG:5514, the area measurement is accurate and uses metric units appropriate for Slovak geographic analysis.

This approach demonstrates advanced spatial operations including buffering, clipping, union, and difference operations to precisely define and measure a complex geographic zone.

### Results

![Task 13 - Geographic Results of Required Territory](img/task_13_geographic_results.png)

![Task 13 - Tabular Results of Required Territory's Area](img/task_13_tabular_results.png)

The geographic visualization shows the 20 km buffer zone surrounding Bratislava (excluding the city districts themselves), clipped to Slovakia's borders. The tabular results display the total area of this peripheral zone in square meter