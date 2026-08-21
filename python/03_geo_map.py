"""
TRACK A - STEP 5a: Geospatial view (Python / folium).

Two maps:
  1. A choropleth of median price by county, joined to the geojson polygons.
  2. A point layer of individual listings coloured by price.

The join key is neighbourhood_cleansed <-> geojson property 'neighbourhood'
(this Twin Cities dataset is COUNTY-level: Hennepin, Ramsey, Dakota, ...).

Run:  python 03_geo_map.py   ->  outputs/map_price.html (open in a browser)
Needs: pandas, folium
"""
import sys
import pandas as pd
import folium
import config as C

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def main():
    df = pd.read_csv(C.LISTINGS_CLEAN)

    by_area = (df.groupby("neighbourhood_cleansed")["price"]
                 .median().reset_index()
                 .rename(columns={"neighbourhood_cleansed": "neighbourhood",
                                  "price": "median_price"}))

    center = [df["latitude"].median(), df["longitude"].median()]
    m = folium.Map(location=center, zoom_start=9, tiles="cartodbpositron")

    folium.Choropleth(
        geo_data=str(C.GEOJSON),
        data=by_area,
        columns=["neighbourhood", "median_price"],
        key_on="feature.properties.neighbourhood",
        fill_color="YlOrRd", fill_opacity=0.6, line_opacity=0.3,
        nan_fill_color="lightgray",
        legend_name="Median nightly price ($) by county",
    ).add_to(m)

    # sample up to 2000 points so the HTML stays light
    pts = df.dropna(subset=["latitude", "longitude", "price"])
    pts = pts.sample(min(2000, len(pts)), random_state=0)
    hi = pts["price"].quantile(0.9)
    layer = folium.FeatureGroup(name="listings (sampled)")
    for _, r in pts.iterrows():
        folium.CircleMarker(
            [r["latitude"], r["longitude"]], radius=2,
            color="crimson" if r["price"] >= hi else "steelblue",
            fill=True, fill_opacity=0.5,
            popup=f'${r["price"]:.0f} · {r["room_type"]}',
        ).add_to(layer)
    layer.add_to(m)
    folium.LayerControl().add_to(m)

    out = C.OUT / "map_price.html"
    m.save(str(out))
    print(f"Saved {out}  (open in a browser)")


if __name__ == "__main__":
    main()
