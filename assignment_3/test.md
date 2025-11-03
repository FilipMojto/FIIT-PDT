## Task 11 - Roads within 10 km range

### SQL Query

To get all roads within 10 km from the crossing border between the two districts, the following query was proposed:

```sql
DROP TABLE IF EXISTS crossing_border;

CREATE TEMP TABLE IF NOT EXISTS crossing_border AS
SELECT ST_Intersection(d1.way, d2.way) AS way,
		d1.name AS district_a,
    	d2.name AS district_b
FROM planet_osm_polygon d1
JOIN planet_osm_polygon d2
ON d1.name = 'okres Pezinok' AND d2.name = 'okres Malacky'
WHERE d1.boundary = 'administrative' AND d2.boundary = 'administrative'
AND d1.admin_level = '8' and d2.admin_level = '8'; 


-- SELECT * FROM crossing_border;

DROP TABLE IF EXISTS border_buffer;

CREATE TEMP TABLE IF NOT EXISTS border_buffer AS
SELECT ST_Transform(ST_buffer(ST_Transform(cb.way, 5514), 10000), 4326) as buffer
FROM crossing_border as cb;

-- SELECT * FROM border_buffer;


DROP TABLE IF EXISTS roads_in_10_km;

CREATE TABLE roads_in_10_km AS
SELECT r.*
FROM border_buffer bb
JOIN planet_osm_roads r ON ST_Within(r.way, bb.buffer);

SELECT * FROM roads_in_10_km;
```

### Interpretation

To get the correct results, several temporary tables were created in a three-stage process:

**1. Crossing Border Table (`crossing_border`)**

This table identifies and extracts the exact boundary line where the two districts meet. Using `ST_Intersection()`, the query computes the geometric intersection between the polygon boundaries of okres Pezinok and okres Malacky. The result is a linear geometry representing their shared border, along with the names of both districts for reference.

**2. Border Buffer Table (`border_buffer`)**

This table creates a 10 km buffer zone around the crossing border line. The operation involves a coordinate transformation workflow: the border geometry is first transformed to EPSG:5514 (S-JTSK) using `ST_Transform()`, then buffered by 10,000 meters (10 km) using `ST_Buffer()`, and finally transformed back to WGS84 (EPSG:4326) for consistency with the original OSM data coordinate system. This buffer represents the area of interest for finding nearby roads.

**3. Roads in 10 km Table (`roads_in_10_km`)**

This final table retrieves all roads that are completely contained within the 10 km buffer zone. The `ST_Within()` function checks whether road geometries are fully inside the buffer polygon, ensuring that only roads entirely within the defined distance from the border are captured. This is more restrictive than `ST_Intersects()`, as it excludes roads that only partially enter the buffer zone or cross its boundary. The result is stored as a permanent table for further analysis or visualization.