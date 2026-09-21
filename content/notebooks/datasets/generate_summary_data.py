from pathlib import Path
import pandas as pd
import threddsclient as tds
import xarray as xr
from IPython.display import clear_output
import requests
from siphon.catalog import TDSCatalog

urls = dict(
    station_obs=["https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/catalog/datasets/station_obs/catalog.xml"],
    gridded_obs=["https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/catalog/datasets/gridded_obs/catalog.xml"],
    reanalyses=["https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/catalog/datasets/reanalyses/catalog.xml"],
    forecasts=["https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/catalog/datasets/forecasts/catalog.xml"],
    simulations=[ "https://esgf.ouranos.ca/thredds/catalog/aggregations/CORDEX-CMIP6/catalog.xml",
                  "https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/catalog/datasets/simulations/catalog.xml"
                ],
)

def walk(cat, depth=1):

    """Return a generator walking a THREDDS data catalog for datasets.

    Parameters
    ----------
    cat : TDSCatalog
      THREDDS catalog.
    depth : int
      Maximum recursive depth.
      Setting 0 will return only datasets within the top-level catalog.
      If None, depth is set to 1000.

    Yields
    ------
    Dataset
        Siphon catalog dataset.
    """
    
    yield from cat.datasets.values()
    
    if depth is None:
        depth = 1000

    if depth > 0:
        for ref in cat.catalog_refs.values():
            try:
                child = ref.follow()
                yield from walk(child, depth=(depth - 1))

            except requests.HTTPError as exc:
                log.exception(exc)

df_cols = {
    "title": [],
    "dataset_id": [],
    "dataset_description": ["further_info_url"],
    "institution": ["institute", "GRIB_centreDescription"],
    "institution_id": ["institute_id", "organisation", "instiution"],
    "start_year": [],
    "end_year": [],
    "abstract": [],
    "processing_level": ["processing"],
    "license": [],
    "license_type": [],
    "project_id": ["mip_era"],
    "frequency": [],
    "variables": [],
    "driving_experiment_id": [
        "GCM__experiment_id",
        "driving_experiment",
        "experiment_id",
        "experiment",
    ],
}

optional = dict(
    station_obs=[
        "abstract",
        "dataset_description",
        "dataset_id",
        "project_id",
        "driving_experiment_id",
        "processing_level",
    ],
    gridded_obs=[
        "abstract",
        "dataset_description",
        "dataset_id",
        "project_id",
        "driving_experiment_id",
        "processing_level",
        "license",
        "license_type",
    ],
    reanalyses=[
        "abstract",
        "dataset_description",
        "dataset_id",
        "project_id",
        "driving_experiment_id",
        "processing_level",
    ],
    forecasts=[
        "abstract",
        "dataset_description",
        "dataset_id",
        "project_id",
        "driving_experiment_id",
        "institution_id",
        "frequency",
        "processing_level",
    ],
    simulations=["abstract", "dataset_description", "dataset_id", "processing_level"],
)


for key, urls in urls.items():
    ds_dict = {}
    opts = optional[key]
    for url in urls:
        cat = TDSCatalog(url)
        
        for dd in walk(cat, depth=10):
            ncml = Path(dd.name).stem
            print(ncml)
            # skip CRCM5-CMIP6 aggs on pavics - use ESGF
            # TODO can remove this once ESGF is used as official prod loc
            if 'OURANOS_CRCM5' in ncml and "https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/catalog/datasets/simulations/" in url:
                continue
            dap_key = [a for a in dd.access_urls if a in ['OPeNDAP', 'OpenDAP']][0]
            if any([v in dd.access_urls[dap_key] for v in ["bccaqv2", "cb-oura-1.0"]]):
                continue
            if "ESPO-R" not in ncml:
                ds_dict[ncml] = dict()
                ds = None
                for ntry in range(0, 5):
                    try:
                        ds = xr.open_dataset(dd.access_urls[dap_key], chunks=dict(time=100))
                        break
                    except:
                        ntry -= 1
                        ds = None
                if ds is None:
                    raise OSError()
                ds_dict[ncml]["path"] = dd.access_urls[dap_key]
                ds_dict[ncml]["thredds_cat"] = url
                for col in df_cols:
    
                    if col == "variables":
                        ds_dict[ncml][col] = ",".join(sorted(list(ds.data_vars)))
                    elif col == "institution" and "CaSR" in ncml:
                        ds_dict[ncml][col] = ds.attrs["institute"]
                    elif col == "institution" and "NRCanMET-daily" in ncml:
                        ds_dict[ncml][col] = "Natural Resources Canada"
                    elif col.endswith("_year"):
                        if "start" in col:
                            ds_dict[ncml][col] = ds.time.min().dt.year.values
                        elif "end" in col:
                            ds_dict[ncml][col] = ds.time.max().dt.year.values
                    else:
                        try:
                            if col not in ds.attrs.keys():
                                col1 = [c for c in df_cols[col] if c in ds.attrs][0]
                                ds_dict[ncml][col] = ds.attrs[col1]
                            else:
    
                                ds_dict[ncml][col] = ds.attrs[col]
                        except:
    
                            if col in opts:
                                ds_dict[ncml][col] = ""
                            else:
                                raise ValueError(f"attr {col} or alias not found")
                chunks = None
                for vv in ds.data_vars:
                    if "time" in ds[vv].dims:
    
                        if (
                            "_ChunkSizes" in ds[vv].attrs
                            and "_bnds" not in vv
                            and vv != "rotated_pole"
                            and vv != "poids"
                            and vv != "time_vectors"
                        ):
    
                            if "realization" not in ds.dims:
                                chunks = {
                                    d: int(ds[vv].attrs["_ChunkSizes"][ii])
                                    for ii, d in enumerate(ds[vv].dims)
                                }
    
                            else:
                                chunks = {
                                    d: int(ds[vv].attrs["_ChunkSizes"][ii])
                                    for ii, d in enumerate(
                                        ds[vv].isel(realization=0).squeeze().dims
                                    )
                                }
                                chunks["realization"] = 1
                            break
    
                if key == "station_obs":
                    ds_dict[ncml]["dask_chunks"] = {"time": -1, "station": 50}
                else:
                    ds_dict[ncml]["dask_chunks"] = chunks
    
                if (
                    "ClimEx" in ds_dict[ncml]["title"]
                    or "CRCM5-CMIP6" in ds_dict[ncml]["title"]
                ):
                    ds_dict[ncml]["processing_level"] = "raw"
                if "ClimEx" in ds_dict[ncml]["title"]:
                    ds_dict[ncml]["dataset_id"] = "ClimEx"
                clear_output()
    df = pd.DataFrame.from_dict(ds_dict, orient="index")
    df.reset_index(inplace=True)
    outcsv = Path(f"dataset_summary_data/{key}.csv")
    outcsv.parent.mkdir(exist_ok=True)
    df.to_csv(outcsv)
    del ds_dict
