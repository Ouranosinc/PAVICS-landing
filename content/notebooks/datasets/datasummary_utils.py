import ast
import html
import logging
import warnings
import xml.etree.ElementTree as ET
from datetime import datetime
from os.path import commonpath
from pathlib import Path

import dask
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import panel as pn
import requests
import xarray as xr
from bokeh.models.widgets.tables import HTMLTemplateFormatter
from bokeh.resources import CDN
from cartopy import crs as ccrs
from dask.distributed import Client
from IPython.display import clear_output
from tqdm.auto import tqdm

stylesheet = """
/* 1. Base style for all cells */
.tabulator-cell {
    font-size: 12px;
}

.tabulator-col-title {
    font-size: 12px !important;
}

"""
dask_kwargs = dict(
    n_workers=6,
    threads_per_worker=10,
    memory_limit="3GB",
    dashboard_address=8787,
    silence_logs=logging.ERROR,
)

max_table_height = 400
max_table_width = 680


open_link = dict(en="\U0001f310 Open link", fr="\U0001f310 Ouvrir lien")
summary_fields = dict()
summary_fields["en"] = dict(
    title="Summary",
    access="Access",
    dataset="Title",
    map="Example of spatial coverage",
    tutorial="PAVICS general tutorials",
    netcdf="NetCDF files",
    location="Analysis ready (OpenDAP)",
    filename="Filename(s)",
    xarray_example="Open with xarray",
    frequency="Frequency",
    temporal_coverage="Temporal coverage",
    license="License",
)
summary_fields["fr"] = dict(
    title="Sommaire",
    dataset="Titre",
    access="Accès",
    map="Exemple de domaine spatial",
    tutorial="Tutoriels généraux PAVICS",
    location="Prêt pour l'analyse (OpenDAP)",
    netcdf="Fichiers NetCDF",
    filename="Nom(s) de fichier(s)",
    xarray_example="Ouvrir avec xarray",
    frequency="Fréquence",
    temporal_coverage="Couverture temporelle",
    license="License",
)


def correct_institutes(df):

    inst = [
        (o.replace(", Victoria, BC, www.pacificclimate.org", "") if "PCIC" in o else o)
        for o in df["institution"]
    ]

    inst = [
        (
            o.replace(
                "Canadian Centre for Climate Services",
                "Canadian Centre for Climate Services : Climatedata.ca",
            )
            if "Canadian Centre for Climate Services" in o
            else o
        )
        for o in inst
    ]

    inst = [
        (
            o.replace(
                "Ouranos Consortium on Regional Climatology and Adaptation to Climate Change",
                "Ouranos",
            )
            if "Ouranos" in o
            else o
        )
        for o in inst
    ]

    inst = [
        (
            o.replace(
                "Natural Resources Canada : Canadian Forest Service",
                "Natural Resources Canada",
            )
            if "Natural Resources Canada : Canadian Forest Service" in o
            else o
        )
        for o in inst
    ]

    df["institution"] = inst
    return df


def correct_titles(df):

    titles = [
        (o.replace("PCIC/ECCC", "CanDCS-U5 : CMIP5") if "(BCCAQv2)" in o else o)
        for o in df["title"]
    ]

    titles = [
        (
            o.replace("PCIC/ECCC :", "CanDCS-M6")
            if "PCIC/ECCC : Canadian Downscaled Climate Scenarios – Multivariate CMIP6"
            in o
            else o
        )
        for o in titles
    ]

    titles = [
        (
            o.replace("PCIC/ECCC", "CanDCS-U6")
            if "PCIC/ECCC Canadian Downscaled Climate Scenarios – Univariate CMIP6" in o
            else o
        )
        for o in titles
    ]

    titles = [
        (
            o.replace("Ouranos", "Ouranos : CMIP5")
            if "Ouranos standard ensemble of bias-adjusted " in o
            else o
        )
        for o in titles
    ]
    titles = [
        o.replace("The ClimEx", "The ClimEx") if "ClimEx" in o else o for o in titles
    ]

    titles = [
        (
            o.replace("ESPO-G6", "ESPO-G6").replace(
                "Ouranos Multipurpose Climate Scenarios",
                "Ouranos Ensemble of Bias-adjusted Simulations",
            )
            if "ESPO-G6" in o
            else o
        )
        for o in titles
    ]

    titles = [
        o.replace("CRCM5-CMIP6", "CRCM5-CMIP6") if "CRCM5-CMIP6" in o else o
        for o in titles
    ]
    titles = [o.replace("PINS v1", "PINS v1") if "PINS v1" in o else o for o in titles]
    df["title"] = titles
    return df


def create_map(dfin, overwrite=False):
    print("create map png", dfin["title"].unique())
    outpng = Path("dataset_map_pngs", f"{dfin['title'].values[0].replace('/','_')}.png")

    if not outpng.exists() or overwrite:
        outpng.parent.mkdir(exist_ok=True)
        # Method 1: Using ast.literal_eval (RECOMMENDED - safe)
        chunks = ast.literal_eval(dfin["dask_chunks"].values[0])
        # chunks = 'auto'
        if "GHCN" in dfin["dataset_id"].iloc[0]:
            infile = [p for p in dfin["path"].values if Path(p).name.startswith("pr_")][
                0
            ]
        else:
            infile = dfin["path"].values[0]
        ds_tmp = xr.open_dataset(infile, chunks=chunks, decode_timedelta=False)
        if "realization" in ds_tmp.dims:
            ds_tmp = ds_tmp.isel(realization=0).squeeze()
        if "member" in ds_tmp.dims:
            ds_tmp = ds_tmp.isel(member=0).squeeze()
        for vv in ds_tmp.data_vars:
            if "time" not in ds_tmp[vv].dims:
                ds_tmp = ds_tmp.assign_coords({vv: ds_tmp[vv]})
        vv = None
        for v in ["tas", "tasmin", "tasmax", "pr", "tg_mean"]:
            if v in ds_tmp.data_vars:
                vv = v
                break
        if vv is None:
            vv = [v for v in ds_tmp.data_vars if "bnds" not in v][0]
        print(vv)
        tt = round(len(ds_tmp[vv].time) / 2)
        data = ds_tmp[vv].isel(time=tt)
        print(len(data.dims))
        if len(data.dims) > 1:
            with Client(**dask_kwargs) as c:
                display(c)
                data = data.load()
        clear_output()

        fig = plt.figure(figsize=(4, 4))
        ax = fig.add_subplot(1, 1, 1, projection=ccrs.LambertConformal())

        # Add map features
        ax.coastlines()
        ax.gridlines()
        if len(data.dims) == 1:
            ax.scatter(x=data.lon, y=data.lat, s=10, transform=ccrs.PlateCarree())
        else:
            data.plot(
                ax=ax, x="lon", y="lat", cmap="RdBu_r", transform=ccrs.PlateCarree()
            )
        ax.set_title("")
        if "ERA5" in outpng.name:
            ax.set_extent([-150, -45, 10, 87.5], crs=ccrs.PlateCarree())
        fig.savefig(outpng, bbox_inches="tight", pad_inches=0)
    return outpng


def color_status(val):
    if val.startswith("[") or "import" in val:
        return (
            #'background-color: #f4f4f4; '   # Light gray background
            "font-family: monospace; "  # Monospaced font
            "color: #d63384; "  # Pinkish code color (common in docs)
        )
    elif val == "Pending":
        return "background-color: yellow"
    return ""


def create_summary_tab(dfin, lang="en"):
    print("create summary table", dfin["title"].unique())
    summ = {}
    # summ[summary_fields[lang]['title']] = ""
    summ[summary_fields[lang]["dataset"]] = dfin.title.values[0]
    chunks = ast.literal_eval(dfin["dask_chunks"].values[0])
    infile = dfin["path"].values[0]
    ds_tmp = xr.open_dataset(infile, chunks=chunks, decode_timedelta=False)
    doi = None
    if "DOI" in ds_tmp.attrs:
        doi = ds_tmp.attrs["DOI"]
    elif "doi" in ds_tmp.attrs:
        doi = ds_tmp.attrs["doi"]
    if doi is not None:
        doi = f'<a href="{doi}" target="_blank">{open_link[lang]}<a />'
        summ["DOI"] = doi
    summ["Institution"] = dfin.institution.values[0]

    first_flag = True
    for p in tqdm(dfin["path"], total=len(dfin["path"])):

        ds_tmp = xr.open_dataset(p, chunks=chunks, decode_timedelta=False)
        max_tmp = ds_tmp.isel(time=-1).time
        min_tmp = ds_tmp.isel(time=0).time
        max_tmp = datetime(
            max_tmp.dt.year.values, max_tmp.dt.month.values, max_tmp.dt.day.values
        )
        min_tmp = datetime(
            min_tmp.dt.year.values, min_tmp.dt.month.values, min_tmp.dt.day.values
        )
        if first_flag:

            max_time = max_tmp
            min_time = min_tmp
            first_flag = False

        else:
            max_time = max(max_time, max_tmp)
            min_time = min(min_time, min_tmp)

    
    if "GEPS" in dfin.title.values[0]:
        tmp_str = "Current forecast"
    elif 'ORRC' in dfin.title.values[0]:
        tmp_str = f"{min_time.strftime("%Y-%m-%d")} - near present"
    else:
        tmp_str = f"{min_time.strftime("%Y-%m-%d")} - {max_time.strftime("%Y-%m-%d")}"    
    summ[summary_fields[lang]["temporal_coverage"]] = tmp_str
    summ[summary_fields[lang]["frequency"]] = dfin["frequency"].values[0]
    summ[summary_fields[lang]["license"]] = dfin["license"].values[0]
    summ = pd.DataFrame.from_dict(summ, orient="index", columns=["info"])
    out = pn.widgets.Tabulator(
        summ,
        header_filters=True,
        sortable=False,
        disabled=True,
        selectable=False,
        height=250,
        configuration={
            "headerVisible": False,  # Hides the column header
            "layout": "fitData",  # This is critical for resizing columns
        },
        stylesheets=[stylesheet],
        theme="bootstrap",
        formatters={
            "info": HTMLTemplateFormatter(),
        },
        max_height=max_table_height,
        max_width=max_table_width,
    )
    # out.style.map(color_status, subset=['info'])
    tit_str = summary_fields[lang]["title"]
    tit_str = f'<p style="font-size: 14px;font-weight: bold;">{tit_str}</p>'
    return pn.Column(pn.pane.HTML(tit_str), out)


def create_variable_tab(dfin, lang="en", overwrite=False):
    print("create variable table", dfin["title"].unique())
    outcsv = Path(
        "dataset_variable_details",
        f"{dfin['title'].values[0].replace('/','_')}_{lang}.csv",
    )

    if not outcsv.exists() or overwrite:

        if lang == "en":
            tmp_grp = "Temporal grouping"
            desc = "Description"
            units = "Units"
            indname = "Variable code"
            cell_name = "Aggregation"
        elif lang == "fr":
            tmp_grp = "Groupement temporel"
            desc = "Déscription"
            units = "Unités"
            indname = "Code variable"
            cell_name = "Agrégation"
        else:
            raise ValueError()
        vars_dict = {}
        # display(dfin)
        print("create var table", dfin["title"].unique())
        for index, row in tqdm(dfin.iterrows(), total=len(dfin)):

            # print(f"Index: {index}, Path: {row['path']}")
            inpath = row["path"]
            chunks = ast.literal_eval(row["dask_chunks"])

            ds_tmp = xr.open_dataset(inpath, chunks=chunks, decode_timedelta=False)

            # set non-time variables as coordinates
            for vv in ds_tmp.data_vars:
                # if "time" not in ds_tmp[vv].dims:
                if not {k for k in chunks.keys() if k != "time"}.issubset(
                    ds_tmp[vv].dims
                ):
                    ds_tmp = ds_tmp.assign_coords({vv: ds_tmp[vv]})

            # Try to infer the time frequency and convert to an interpretable label
            xrfreq = xr.infer_freq(ds_tmp.time)
            if xrfreq is None:
                if any([m in inpath for m in ["_mon_", "monthly"]]):
                    xrfreq = "MS"
                elif "GEPS_latest" in inpath:
                    xrfreq = "GEPS"
                else:
                    continue
            if any([m in inpath for m in ["30yAvg"]]):
                xrfreq = "30CLIM"
            if "anusplin_v1_climindices_gridded" in inpath:
                xrfreq = "YS"
            freq_map = {
                "YS": "annual",
                "YS-JAN": "annual",
                "YS-JUL": "annual-julyjune",
                "YS-AUG": "annual-augjuly",
                "QS-DEC": "seasonal",
                "2QS-OCT": "6month",
                "MS": "monthly",
                "annual-JAN": "annual",
                "annual-JUL": "annual-julyjune",
                "D": "daily",
                "h": "hourly",
                "3h": "3-hourly",
                "6h": "6-hourly",
                "30CLIM": "30y average",
                "GEPS": "mixed: 3-hourly and 6-hourly",
            }
            freq = freq_map[xrfreq]

            # For CanDCS-M6, variables are often named like "ssp245_tx_mean".
            # We remove the scenario prefix so the variable ID is just "tx_mean".
            for vv in [v for v in ds_tmp.data_vars if "_consensus" not in v]:
                vv_out = vv if "ssp" not in vv else "_".join(vv.split("_")[1:])
                if "time" in ds_tmp[vv].dims:
                    freqout = freq
                else:
                    freqout = "invariant"

                if vv_out not in vars_dict:
                    desc_str = ds_tmp[vv].attrs.get("long_name", "")

                    cell_str = ds_tmp[vv].attrs.get("cell_methods", "")
                    vars_dict[vv_out] = {
                        tmp_grp: freqout,
                        desc: desc_str,
                        cell_name: cell_str,
                        units: ds_tmp[vv].attrs.get("units", ""),
                    }
                else:
                    if freqout not in vars_dict[vv_out][tmp_grp]:
                        vars_dict[vv_out][tmp_grp] = (
                            vars_dict[vv_out][tmp_grp] + "; " + freqout
                        )
        # cleaned = clean_for_df(vars_dict)
        # print(cleaned)
        # vars_table = sanitize_tabulator_data(vars_dict)#
        tmp_df = pd.DataFrame.from_dict(vars_dict, orient="index").sort_index()

        groups = {name: group.sort_index() for name, group in tmp_df.groupby(tmp_grp)}
        df_list = [g for ii, g in groups.items() if ii != "invariant"]
        if "invariant" in groups.keys():
            df_list.append(groups["invariant"])
        vars_table = pd.concat(df_list)
        # vars_table = tmp_df.groupby(tmp_grp).apply(lambda x: x.sort_index())

        vars_table.index.name = indname
        vars_table = vars_table[
            [
                desc,
                units,
                tmp_grp,
                cell_name,
            ]
        ]
        outcsv.parent.mkdir(exist_ok=True, parents=True)
        vars_table.to_csv(outcsv)
        del vars_table

    vars_table = pd.read_csv(outcsv, index_col=0)

    tit_str = f'<p style="font-size: 14px;font-weight: bold;">Variables</p>'
    return pn.Column(
        pn.pane.HTML(tit_str),
        pn.widgets.Tabulator(
            vars_table,
            header_filters=True,
            disabled=True,
            sortable=True,
            selectable=False,
            page_size=10,
            max_height=max_table_height,
            max_width=max_table_width,
            configuration={
                "layout": "fitData",  # This is critical for resizing columns
            },
            stylesheets=[stylesheet],
        ),
    )


def download_file(url, output_path=None):
    """Download a file using requests"""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()  # Raise an error for bad status codes

        # Write to file
        with open(output_path, "wb") as f:
            f.write(response.content)

        # print(f"✓ File downloaded successfully: {output_path}")
        # print(f"  File size: {len(response.content) / 1024:.2f} KB")

    except requests.exceptions.Timeout:
        print("✗ Error: Request timed out")
    except requests.exceptions.ConnectionError:
        print("✗ Error: Failed to connect to the server")
    except requests.exceptions.HTTPError as e:
        print(f"✗ HTTP Error: {e.response.status_code}")
    except Exception as e:
        print(f"✗ Error: {e}")


def parse_ncml(file_path):
    """
    Parse NCML file and extract all scan locations and netcdf locations.

    Args:
        file_path: Path to the NCML file

    Returns:
        dict: Dictionary containing 'scan_locations' and 'netcdf_locations' lists
    """
    # Register namespace to handle the XML namespace properly
    namespace = {"ncml": "http://www.unidata.ucar.edu/namespaces/netcdf/ncml-2.2"}

    tree = ET.parse(file_path)
    root = tree.getroot()

    locations = []

    # Check root netcdf element for location attribute
    root_location = root.get("location")
    if root_location:
        locations.append(root_location)

    # Find all scan elements with location attribute
    for scan in root.findall(".//ncml:scan", namespace):
        location = scan.get("location")
        if location:
            locations.append(location)

    # Find all netcdf elements with location attribute
    for netcdf in root.findall(".//ncml:netcdf[@location]", namespace):
        location = netcdf.get("location")
        if location:
            locations.append(location)

    return locations


def create_access_table(dfin, lang="en"):
    print("create access table", dfin["title"].unique())
    if lang == "en":
        tmp_title = "Temporal files"
        fx_title = "Invariant files"
        title = "Data access"
        agg_title = "NcML aggregations"
    elif lang == "fr":
        title = "Accès aux Données"
        tmp_title = "Fichiers temporels"
        fx_title = "Fichiers invariants"
        agg_title = "Aggrégations NcML"
    filenames = [Path(p).name for p in dfin.path]

    thrds_access = f"https://{'/'.join([p for p in dfin['path'].values[0].split('//')[-1].split('/')[0:-1]])}/catalog.html".replace(
        "dodsC", "catalog"
    )

    access = {}
    tut = f'<a href="https://pavics.ouranos.ca/climate_analysis.html#a" target="_blank">{open_link[lang]}<a />'
    access[summary_fields[lang]["tutorial"]] = tut

    locs = []
    for p in dfin.path:
        https = p.replace("/dodsC/", "/fileServer/")
        outfile = Path(p).name
        download_file(https, outfile)
        locs.extend(parse_ncml(outfile))
        Path(outfile).unlink()
    fx_locs = [Path(l) for l in locs if "/fx/" in l]
    tmp_locs = [Path(l) for l in locs if "/fx/" not in l]
    if len(fx_locs) == 1:
        fx_locs = fx_locs[0].parent.as_posix()
    else:
        fx_locs = commonpath(fx_locs) if fx_locs else fx_locs
    thrds_str = ""
    if len(tmp_locs) == 1:
        tmp_locs = tmp_locs[0].parent.as_posix()
    else:
        tmp_locs = commonpath(tmp_locs) if tmp_locs else tmp_locs
    if tmp_locs:
        tmp_locs = tmp_locs.replace(
            "/pavics-data/",
            "https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/catalog/birdhouse/",
        )
    if fx_locs:
        fx_locs = fx_locs.replace(
            "/pavics-data/",
            "https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/catalog/birdhouse/",
        )
    if tmp_locs:
        if not fx_locs or fx_locs == tmp_locs:
            thrds_str = (
                thrds_str
                + f'<a href="{tmp_locs}/catalog.html" target="_blank">{open_link[lang]}<a />'
            )
        else:
            thrds_str = (
                thrds_str
                + f'<a href="{tmp_locs}/catalog.html" target="_blank">{tmp_title}<a />'
            )
    if fx_locs and fx_locs != tmp_locs:
        thrds_str = (
            thrds_str
            + "<br>"
            + f'<a href="{fx_locs}/catalog.html" target="_blank">{fx_title}<a />'
        )
    access[summary_fields[lang]["netcdf"]] = thrds_str
    agg_str = f'<a href="{thrds_access}" target="_blank">{agg_title}<a />'
    access[summary_fields[lang]["location"]] = agg_str
    file_str = "[" + ", ".join(f'"{ncml}"' for ncml in filenames) + "]"
    access[summary_fields[lang]["filename"]] = file_str

    code_str = f"""
<pre style="white-space: pre-wrap; word-wrap: break-word; margin: 0;">
<code>
from siphon.catalog import TDSCatalog
import xarray as xr
url = "{thrds_access}"
cat = TDSCatalog(url)
ncml_files = {file_str} # optionally specify files of interest
opendap_urls = [cat.datasets[x].access_urls['OpenDAP'] for x in cat.datasets]

if ncml_files:
    opendap_urls = [o for o in opendap_urls if o.split("/")[-1] in ncml_files]

for od in opendap_urls:
    chunks = {ast.literal_eval(dfin['dask_chunks'].values[0])}
    ds = xr.open_dataset(od, chunks=chunks, decode_timedelta=False)
    ## add more code here
</code>
</pre>
"""

    access[summary_fields[lang]["xarray_example"]] = code_str
    ## create table
    access = pd.DataFrame.from_dict(access, orient="index", columns=["info"])
    tit_str = f'<p style="font-size: 14px;font-weight: bold;">{title}</p>'
    out = pn.widgets.Tabulator(
        access,
        header_filters=True,
        sortable=False,
        disabled=True,
        selectable=False,
        min_height=200,
        sizing_mode="stretch_width",
        configuration={
            "headerVisible": False,  # Hides the column header
            "layout": "fitData",  # This is critical for resizing columns
        },
        stylesheets=[stylesheet],
        theme="bootstrap",
        formatters={
            "info": HTMLTemplateFormatter(),
        },
        max_height=max_table_height,
        max_width=max_table_width,
    )
    out.style.map(color_status, subset=["info"])
    return pn.Column(pn.pane.HTML(tit_str), out)


def get_html(file):
    with open(file, encoding="utf-8") as f:
        html_content = f.read()

    # 2. Escape it cleanly to prevent broken string syntax in python
    escaped_content = html.escape(html_content)

    # 3. Mount it securely using an active document iframe configuration
    iframe_string = f'<iframe srcdoc="{escaped_content}" style="width:100%; height:800px; border:none;"></iframe>'

    return iframe_string


def create_summary_tabs(dfin, lang="en", overwrite=False):
    id = dfin["title"].unique()[0]
    mappng = create_map(dfin, overwrite=overwrite)
    map_str = summary_fields[lang]["map"]
    map_str = f'<p style="font-size: 14px;font-weight: bold;">{map_str}</p>'
    mappng = pn.Column(pn.pane.HTML(map_str), pn.pane.PNG(mappng))

    summ = create_summary_tab(dfin, lang=lang)
    summ = pn.Row(mappng, summ)

    acc1 = create_access_table(dfin, lang=lang)
    acc1 = pn.Row(mappng, acc1, width_policy="min", height_policy="min")

    var1 = create_variable_tab(dfin, lang=lang)
    var1 = pn.Row(mappng, var1, width_policy="min", height_policy="min")

    tabs = pn.Tabs(
        (summary_fields[lang]["title"], summ),
        ("Variables", var1),
        (summary_fields[lang]["access"], acc1),
        max_width=max_table_width + 450,
    )
    return pn.Column(tabs)
