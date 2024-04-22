import xarray as xr
import threddsclient as tds
from pathlib import Path
from IPython.display import clear_output
import pandas as pd
urls = dict(
            station_obs="https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/catalog/datasets/station_obs/catalog.html",
            gridded_obs= "https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/catalog/datasets/gridded_obs/catalog.html",
            reanalyses="https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/catalog/datasets/reanalyses/catalog.html",
            forecasts="https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/catalog/datasets/forecasts/catalog.html",
            simulations="https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/catalog/datasets/simulations/catalog.html",
           )


df_cols = {'title':[],'dataset_id':[], 'dataset_description':[],'institution':['institute', 'GRIB_centreDescription'], 'institution_id':['institute_id'],
           'start_year':[], 'end_year':[],'abstract':[],'processing_level':['processing'], 'license':[],'license_type':[], 'project_id':['mip_era'], 'frequency':[], 'variables':[], 
           'driving_experiment_id':['GCM__experiment_id', 'driving_experiment', 'experiment_id','experiment']}

optional = dict(
                station_obs =['abstract', 'dataset_description','dataset_id', 'project_id', 'driving_experiment_id', 'processing_level'],
                gridded_obs = ['abstract', 'dataset_description','dataset_id', 'project_id', 'driving_experiment_id', 'processing_level'],
                reanalyses=['abstract', 'dataset_description','dataset_id', 'project_id', 'driving_experiment_id', 'processing_level'],
                forecasts=['abstract', 'dataset_description','dataset_id', 'project_id', 'driving_experiment_id', 'institution_id', 'frequency', 'processing_level'],
                simulations=['abstract', 'dataset_description', 'dataset_id', 'processing_level'],
               )

for key, url in urls.items(): 
    ds_dict= {}
    opts = optional[key]
    for dd in tds.crawl(url, depth=10):
        ncml = Path(dd.name).stem
        print(ncml)
        if 'ESPO-R' not in ncml:
            ds_dict[ncml] = dict()
            ds = xr.open_dataset(dd.opendap_url(),chunks=dict(time=100))
            ds_dict[ncml]['path']=dd.opendap_url()
            ds_dict[ncml]['thredds_cat'] = url
            for col in df_cols:
                print(col)
                if col == 'variables':
                    ds_dict[ncml][col] = ",".join(sorted(list(ds.data_vars)))
                elif col.endswith('_year'):
                    if 'start' in col:
                        ds_dict[ncml][col] = ds.time.min().dt.year.values
                    elif 'end' in col:  
                        ds_dict[ncml][col] = ds.time.max().dt.year.values
                else:
                    try:
                        if col not in ds.attrs.keys():
                            col1 = [c for c in df_cols[col] if c in ds.attrs][0]
                            ds_dict[ncml][col] = ds.attrs[col1]
                        else:
                        
                            ds_dict[ncml][col] = ds.attrs[col]
                    except:
                        print(col)
                        if col in opts:
                            ds_dict[ncml][col] = ""
                        else:
                            raise ValueError(f'attr {col} or alias not found')
            chunks = None
            for vv in ds.data_vars:
                if 'time' in ds[vv].dims:
                    print(vv)
                    if '_ChunkSizes' in ds[vv].attrs and '_bnds' not in vv and vv != 'rotated_pole':
                        #print(ds[vv].attrs['_ChunkSizes'])
                        if 'realization' not in ds.dims: 
                            chunks = {d:ds[vv].attrs['_ChunkSizes'][ii] for ii,d in enumerate(ds[vv].dims)}
                            print(chunks)
                        else:
                            chunks = {d:ds[vv].attrs['_ChunkSizes'][ii] for ii,d in enumerate(ds[vv].isel(realization=0).squeeze().dims)}
                            chunks['realization'] = 1
                        break
            
            if key == 'station_obs':
                ds_dict[ncml]['dask_chunks'] = {'time':-1, 'station':1}
            else:
                ds_dict[ncml]['dask_chunks'] = chunks
            
            if 'ClimEX' in ds_dict[ncml]['title'] or 'CRCM5-CMIP6' in ds_dict[ncml]['title']:
                ds_dict[ncml]['processing_level'] = 'raw'
            clear_output()
    df = pd.DataFrame.from_dict(ds_dict, orient='index')
    df.reset_index(inplace=True)
    outcsv = Path(f"dataset_summary_data/{key}.csv")
    outcsv.parent.mkdir(exist_ok=True)
    df.to_csv(outcsv)
    del ds_dict