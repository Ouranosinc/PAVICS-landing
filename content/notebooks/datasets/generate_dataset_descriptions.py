import re
import shutil
import warnings
from pathlib import Path

import geopandas as gpd
import git
import holoviews as hv
import hvplot
import hvplot.pandas
import hvplot.xarray
import intake_esm
import numpy as np
import pandas as pd
import panel as pn
import requests
import xarray as xr
from bokeh.models.tools import HoverTool
from dask.diagnostics import ProgressBar
from IPython.display import HTML, Markdown
from shapely.geometry import Polygon
from siphon.catalog import TDSCatalog
from xclim.core import units

repo = git.Repo(".", search_parent_directories=True)
repo = Path(repo.git_dir).parent

warnings.simplefilter("ignore")

u = "https://pavics.ouranos.ca/catalog/"

src = requests.get(u).text

m = re.findall('href="(.*?)"', src)
intake_path = Path("intake_cats")
for fn in m:
    if ".." in fn:
        continue
    print(f"downloading {fn}")
    r = requests.get(u + fn)
    open(intake_path.joinpath(fn), "wb").write(r.content)

# shutil.rmtree(intake_path)
# intake_path.mkdir()
# shutil.copytree("/tmp/intake/", intake_path, dirs_exist_ok=True)

cats = sorted(
    l
    for l in list(intake_path.glob("*.json"))
    if l.name != "cmip5.json" and l.name != "biasadjusted5.json"
)


def _correct_titles(df):
    titles = [
        o.replace("PCIC/ECCC", "PCIC/ECCC : CMIP5") if "(BCCAQv2)" in o else o
        for o in df["title"]
    ]

    titles = [
        o.replace("PCIC/ECCC", "PCIC/ECCC : CMIP6")
        if "PCIC/ECCC Canadian Downscaled Climate Scenarios – Univariate CMIP6" in o
        else o
        for o in titles
    ]
    titles = [
        o.replace("Ouranos", "Ouranos : CMIP5")
        if "Ouranos standard ensemble of bias-adjusted " in o
        else o
        for o in titles
    ]
    titles = [
        o.replace("The ClimEx", "Ouranos : The ClimEx") if "ClimEx" in o else o
        for o in titles
    ]

    titles = [
        o.replace("ESPO-G6", "Ouranos : ESPO-G6") if "ESPO-G6" in o else o
        for o in titles
    ]

    df["title"] = titles
    return df


# options_dict["Datasets_1-Climate_Simulations"] = [o.replace('PCIC/ECCC', 'PCIC/ECCC : CMIP5') if "(BCCAQv2)" in o else o for o in options_dict["Datasets_1-Climate_Simulations"]]
# options_dict["Datasets_1-Climate_Simulations"] = [o.replace('PCIC/ECCC', 'PCIC/ECCC : CMIP6') if "PCIC/ECCC Canadian Downscaled Climate Scenarios – Univariate CMIP6" in o else o for o in options_dict["Datasets_1-Climate_Simulations"]]
# options_dict["Datasets_1-Climate_Simulations"] = [o.replace('Ouranos', 'Ouranos : CMIP5') if "Ouranos standard ensemble of bias-adjusted " in o else o for o in options_dict["Datasets_1-Climate_Simulations"]]
# options_dict["Datasets_1-Climate_Simulations"] = [o.replace('The ClimEx', 'Ouranos : The ClimEx') if "ClimEx" in o else o for o in options_dict["Datasets_1-Climate_Simulations"]]


## Climate simulations - bias adjusted
# bias adjusted
world = gpd.read_file(
    "https://pavics.ouranos.ca/geoserver/public/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=public:global_admin_boundaries&maxFeatures=50000&outputFormat=application%2Fjson"
)
world = gpd.GeoDataFrame(geometry=world.simplify(0.05))

options_dict = {}
options_dict["Datasets_1-Climate_Simulations"] = []
options = []
for c in [c for c in cats if "biasadjusted.json" in c.name or "climex.json" in c.name]:
    cat = intake_esm.intake.open_esm_datastore(c)
    cat.df = _correct_titles(cat.df)
    options.extend(list(cat.df["title"].unique()))

options_dict["Datasets_1-Climate_Simulations"].extend(
    [o for o in options if "Ouranos" in o and "ESPO-R" not in o]
)
options_dict["Datasets_1-Climate_Simulations"].extend(
    [o for o in options if "Ouranos" not in o and "ClimEx" not in o and "NASA" not in o]
)


options_dict["Datasets_2-Observations"] = []
for c in [c for c in cats if "obs.json" in c.name]:
    cat = intake_esm.intake.open_esm_datastore(c)
    options_dict["Datasets_2-Observations"].extend(list(cat.df["title"].unique()))

options_dict["Datasets_3-Reanalysis"] = []
for c in [c for c in cats if "reanalysis.json" in c.name]:
    cat = intake_esm.intake.open_esm_datastore(c)
    options = list(cat.df["title"].unique())

options_dict["Datasets_3-Reanalysis"].extend([o for o in options if "RDRS" in o])

options_dict["Datasets_3-Reanalysis"].extend([o for o in options if "ERA5-Land" in o])

options_dict["Datasets_3-Reanalysis"].extend(
    [o for o in options if o not in options_dict["Datasets_3-Reanalysis"]]
)


options_dict["Datasets_4-forecasts"] = []
for c in [c for c in cats if "forecast.json" in c.name]:
    cat = intake_esm.intake.open_esm_datastore(c)
    options_dict["Datasets_4-forecasts"].extend(list(cat.df["title"].unique()))

for o in options_dict.keys():
    print(o)
    options1 = options_dict[o]
    title_w = pn.widgets.Select(options=options1)

    lang = "en"

    # title_w
    @pn.depends(title_w.param.value)
    def create_data_summary(dataset=title_w.param.value):
        summary_fields = dict()
        summary_fields["en"] = dict(
            title="Summary",
            dataset="dataset",
            tutorial="tutorial",
            location="location",
            filename="filename",
            project="project (processing level)",
            frequency="frequency",
            temporal_coverage="temporal coverage",
            variables="variables",
            driving_experiment="driving experiment(s)",
        )
        summary_fields["fr"] = dict(
            title="Sommaire",
            dataset="jeu de données",
            tutorial="tutoriel",
            location="emplacement",
            filename="nom de fichier",
            project="projet (niveau de traitement)",
            frequency="fréquence",
            temporal_coverage="couverture temporelle",
            variables="variables",
            driving_experiment="expérience(s) de pilotage",
        )
        details_fields = dict()
        details_fields["en"] = dict(
            title="Details", more_info="more info", abstract="abstract"
        )
        details_fields["fr"] = dict(
            title="Détails", more_info="plus d'info", abstract="résumé"
        )

        legal_fields = dict()
        legal_fields["en"] = dict(
            title="License / Terms of use",
            license_type="license type",
            license="license",
        )
        legal_fields["fr"] = dict(
            title="Licence / Conditions",
            license_type="type de licence",
            license="licence",
        )
        df = None
        for c in cats:
            cat = intake_esm.intake.open_esm_datastore(c)
            cat.df = _correct_titles(cat.df)
            if len(cat.search(title=dataset).df) > 0:
                df = cat.search(title=dataset).df
                if "ESPO-G6" in dataset:
                    df["project_id"] = "CMIP6"
                break
        print(df["path"][0])
        # if "cmip6" in df["path"][0]:
        #     cat = intake_esm.intake.open_esm_datastore(
        #         c.parent.joinpath("biasadjusted.json")
        #     )
        #     cat.df = _correct_titles(cat.df)
        #     df = cat.search(title=dataset).df
        #     df["project_id"] = "CMIP6"
        #     df["processing"] = "bias_adjusted"
        ds = xr.open_dataset(df["path"][0], chunks=dict(time=1))
        if (
            dataset
            == "PCIC/ECCC : CMIP6 Canadian Downscaled Climate Scenarios – Univariate CMIP6"
        ):  # df['dataset_id'][0] == 'CanDCS-U6':
            df["driving_experiment"] = ds.attrs["GCM__experiment_id"]
            df["driving_model"] = ds.attrs["GCM__model_id"]
            df["institute"] = ds.attrs["institution"]

        if "longitude" in ds.dims:
            ds = ds.rename({"longitude": "lon"})
        if "latitude" in ds.dims:
            ds = ds.rename({"latitude": "lat"})
        if "member" in ds.dims:
            ds = ds.isel(member=0)
        if np.all(ds.lon.values >= 0):
            lons = ds.lon.values
            lons[lons >= 180] = lons[lons >= 180] - 360
            ds = ds.assign_coords(lon=lons)
        if "realization" in ds.dims:
            ds = ds.isel(realization=0).squeeze()
        if {"lat", "lon"}.issubset(set(list(ds.dims.keys()))):
            ds = ds.sortby(["lat", "lon"])
        if "ESPO-G6-R2" in df["path"][0] or "RDRS" in df["path"][0]:
            ds["lon"] = ds.lon.where(ds.lon < 0)
        xlim = (float(ds.lon.min().values), float(ds.lon.max().values))
        ylim = (float(ds.lat.min().values), float(ds.lat.max().values))

        polygon = Polygon(
            [
                (xlim[0], ylim[0]),
                (xlim[0], ylim[1]),
                (xlim[1], ylim[1]),
                (xlim[1], ylim[0]),
                (xlim[0], ylim[0]),
            ]
        )
        poly_gdf = gpd.GeoDataFrame([1], geometry=[polygon], crs=world.crs)
        try:
            world1 = gpd.clip(world, poly_gdf)
        except:
            world1 = world.copy()
        lic = ds.attrs["license"]

        # bias corr specific info
        if "driving_experiment" in df.columns:
            if "ESPO-G6" in df["path"][0]:
                if "experiment_id" in ds.attrs:
                    df["driving_experiment"] = ds.attrs["experiment_id"]

            exp1 = [d.split(",") for d in df["driving_experiment"].unique()]
            exp1 = sorted(list({x for l in exp1 for x in l}))
        else:
            exp1 = None

        if "project_id" in df.columns and "processing" in df.columns:
            prj1 = f"{df['project_id'].unique()[0]} ({df['processing'].unique()[0]})"
        else:
            prj1 = None

        w = 175

        ## summary info
        thrds_access = f"https://{'/'.join([p for p in df['path'][0].split('//')[-1].split('/')[0:-1]])}/catalog.html".replace(
            "dodsC", "catalog"
        )
        if len(df["path"]) == 1:
            ncmls = df["path"][0].split("//")[-1].split("/")[-1]
        else:
            ncmls = f"ensemble of {len(df['path'])} files"

        doi = None

        if "doi" in ds.attrs:
            doi = ds.attrs["doi"]
            doi = f'<a href="{doi}" target="_blank">DOI<a />'

        if doi:
            dataset1 = f"{dataset} ({doi})"
        else:
            dataset1 = dataset

        summary = pn.Column(
            pn.Row(
                pn.pane.HTML(
                    f"{summary_fields[lang]['dataset']} :",
                ),
                pn.pane.HTML(
                    f"{dataset1}",
                ),
            )
        )

        summary.append(
            pn.Row(
                pn.pane.HTML(
                    f"{summary_fields[lang]['tutorial']} :",
                ),
                pn.pane.HTML(
                    f'<a href="/climate_analysis.html" target="_blank">PAVICS data access tutorial<a />',
                ),
            )
        )

        summary.append(
            pn.Row(
                pn.pane.HTML(
                    f"{summary_fields[lang]['location']} ({summary_fields[lang]['filename']}):",
                ),
                pn.pane.HTML(
                    f'<a href="{thrds_access}" target="_blank">THREDDS catalog<a />'
                    + f" ({ncmls})"
                ),
            )
        )

        inst_field = "institution" if "institution" in df.columns else "institute"

        summary.append(
            pn.Row(
                pn.pane.HTML("institution :"), pn.pane.HTML(df[inst_field].unique()[0])
            )
        )

        if prj1:
            summary.append(
                pn.Row(
                    pn.pane.HTML(
                        f"{summary_fields[lang]['project']} :",
                    ),
                    pn.pane.HTML(prj1),
                )
            )
        if "frequency" in df.columns:
            freq = df["frequency"].unique()[0]
            if isinstance(freq, float):
                freq = str(freq)
            summary.append(
                pn.Row(
                    pn.pane.HTML(
                        f"{summary_fields[lang]['frequency']} :",
                    ),
                    pn.pane.HTML(freq),
                )
            )
        if o == "Datasets_4-forecasts":
            summary.append(
                pn.Row(
                    pn.pane.HTML(
                        f"{summary_fields[lang]['temporal_coverage']} :",
                    ),
                    pn.pane.HTML(f"current forecast"),
                )
            )
        else:
            summary.append(
                pn.Row(
                    pn.pane.HTML(
                        f"{summary_fields[lang]['temporal_coverage']} :",
                    ),
                    pn.pane.HTML(
                        f"{ds.time.min().dt.strftime('%Y/%m/%d').values} - {ds.time.max().dt.strftime('%Y/%m/%d').values}"
                    ),
                )
            )

        if "Climatedata.ca" not in dataset:
            summary.append(
                pn.Row(
                    pn.pane.HTML(
                        f"{summary_fields[lang]['variables']} :",
                    ),
                    pn.pane.HTML(", ".join(sorted(v for v in ds.data_vars))),  # noqa
                )
            )
        if exp1:
            summary.append(
                pn.Row(
                    pn.pane.HTML(
                        f"{summary_fields[lang]['driving_experiment']} :",
                    ),
                    pn.pane.HTML(", ".join(exp1)),
                )
            )

        out = pn.Tabs((summary_fields[lang]["title"], summary))

        ## details

        details = pn.Column(
            pn.Row(
                pn.pane.HTML(f"{details_fields[lang]['abstract']} : "),
                pn.pane.HTML(
                    ds.attrs["abstract"],
                ),
            )
        )
        for check in ["bias_adjust", "target_data", "target_ref"]:
            for attr in [attr for attr in ds.attrs if check in attr]:
                details.append(
                    pn.Row(
                        pn.pane.HTML(
                            f"{attr.replace('_', ' ')}: ",
                        ),
                        pn.pane.HTML(
                            ds.attrs[attr],
                        ),
                    )
                )

        details.append(
            pn.Row(
                pn.pane.HTML(f"{details_fields[lang]['more_info']} : "),
                pn.pane.HTML(
                    ds.attrs["dataset_description"],
                ),
            )
        )
        out.append((details_fields[lang]["title"], details))

        ## legal

        legal = pn.Column(
            pn.Row(
                pn.pane.HTML(
                    f"{legal_fields[lang]['license_type']} :",
                ),
                pn.pane.HTML(
                    ds.attrs["license_type"],
                ),
            )
        )
        legal.append(
            pn.Row(
                pn.pane.HTML(
                    f"{legal_fields[lang]['license']} :",
                ),
                pn.pane.HTML(
                    ds.attrs["license"],
                ),
            )
        )

        for check in ["attribution", "citation", "terms"]:
            for attr in [attr for attr in ds.attrs if check in attr]:
                attr_name = attr.replace("_", " ")
                if lang == "fr":
                    attr_name = attr_name.replace(
                        "terms of use", "conditions d'utilisation"
                    )
                legal.append(
                    pn.Row(
                        pn.pane.HTML(
                            f"{attr_name}: ",
                        ),
                        pn.pane.HTML(
                            ds.attrs[attr],
                        ),
                    )
                )

        out.append((legal_fields[lang]["title"], legal))

        ## map

        if {"lat", "lon"}.issubset(set(list(ds.dims.keys()))) or {
            "rlat",
            "rlon",
        }.issubset(set(list(ds.dims.keys()))):
            v = sorted(list(ds.data_vars.keys()), reverse=True)
            for vv in v:
                if len(ds[vv].dims) >= 3:
                    break
            if units.units2pint(ds[vv]) == "kelvin":
                unit_str = "°K"
            else:
                unit_str = units.pint2cfunits(units.units2pint(ds[vv]))
            title = {}
            title[
                "en"
            ] = f"Example of spatial domain : single time-step for variable {vv} ({unit_str})"
            title[
                "fr"
            ] = f"Exemple de domaine spatial: pas de temps unique pour variable {vv} ({unit_str})"
            if {"lat", "lon"}.issubset(set(list(ds.dims.keys()))):
                arr = ds[vv].isel(time=0).load()
                map1 = arr.hvplot.image(
                    title=title[lang],
                    x="lon",
                    y="lat",
                    xlim=xlim,
                    ylim=ylim,
                    rasterize=True,
                    cmap="RdBu_r",
                    hover=False,
                    xlabel="longitude",
                    ylabel="latitude",
                    frame_height=300,
                    frame_width=750,
                ).opts(toolbar=None, fontsize={"title": 12}) * world1.hvplot(c="")
            else:
                arr = ds[vv].isel(time=0).load()
                map1 = arr.hvplot.quadmesh(
                    title=title[lang],
                    x="lon",
                    y="lat",
                    xlim=xlim,
                    ylim=ylim,
                    rasterize=True,
                    cmap="RdBu_r",
                    hover=False,
                    xlabel="longitude",
                    ylabel="latitude",
                    frame_height=300,
                    frame_width=750,
                ).opts(toolbar=None, fontsize={"title": 12}) * world1.hvplot(c="")

        else:
            vars = list(ds.data_vars)
            vars.remove("lat")
            vars.remove("lon")
            df1 = ds.drop_vars(vars).isel(time=0).to_dataframe()

            map1 = world1.hvplot(c="") * df1.hvplot.points(
                "lon",
                "lat",
                xlim=xlim,
                ylim=ylim,
                hover_cols=["station", "station_name"],
                frame_height=300,
                frame_width=750,
            )

        out1 = pn.Column(map1, out)
        return out1

    MAX_WIDTH = 800

    pn.config.sizing_mode = "stretch_width"

    spacer = pn.Spacer(height=0, margin=0)
    # link = pn.pane.HTML(f'<a href="/climate_analysis.html" target="_blank">PAVICS data access tutorial<a />')
    del lang
    with ProgressBar():
        for lang in ["fr", "en"]:
            main_content = pn.Column(
                title_w,
                create_data_summary,
                sizing_mode="stretch_width",
                max_width=MAX_WIDTH,
                align="center",
            )

            main_area = pn.Column(
                spacer,  # TRICK: WONT WORK WITHOUT. YOU CAN SET HEIGHT TO 0 TO NOT TAKE UP HEIGHT
                main_content,
                sizing_mode="stretch_both",
            )
            from bokeh.resources import CDN

            outhtml = f"{o}.html"
            if lang == "fr":
                outhtml = f"{o}_{lang}.html"

            # main_area.show()
            main_area.save(outhtml, embed=True, resources=CDN)
            outdir = repo.joinpath("src/assets/notebooks")
            shutil.copy(outhtml, outdir.as_posix())
