from siphon.catalog import TDSCatalog
import intake_esm
import xarray as xr
from pathlib import Path
from IPython.display import HTML, Markdown
import panel as pn
import numpy as np
import hvplot
import hvplot.pandas
import hvplot.xarray
from bokeh.models.tools import HoverTool
import pandas as pd
import holoviews as hv
from xclim.core import units
import geopandas as gpd
import warnings
import shutil
import git
from shapely.geometry import Polygon
repo = git.Repo('.', search_parent_directories=True)
repo = Path(repo.git_dir).parent

warnings.simplefilter('ignore')


intake_path = Path('intake_cats')
cats = sorted([l for l in list(intake_path.glob('*.json')) if l.name != 'cmip5.json'])

## Climate simulations - bias adjusted
# bias adjusted
world = gpd.read_file(
    'https://pavics.ouranos.ca/geoserver/public/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=public:global_admin_boundaries&maxFeatures=50000&outputFormat=application%2Fjson')
world = gpd.GeoDataFrame(geometry=world.simplify(0.05))

options_dict = {}
options_dict['Datasets_1-Climate_Simulations'] = []
options = []
for c in [c for c in cats if 'biasadjusted.json' in c.name or 'climex.json' in c.name]:
    cat = intake_esm.intake.open_esm_datastore(c)
    options.extend(list(cat.df['title'].unique()))
options_dict['Datasets_1-Climate_Simulations'].extend([o for o in options if 'Ouranos' in o])
options_dict['Datasets_1-Climate_Simulations'].extend([o for o in options if 'ClimEx' in o])
options_dict['Datasets_1-Climate_Simulations'].extend([o for o in options if 'Ouranos' not in o and 'ClimEx' not in o])

options_dict['Datasets_2-Observations'] = []
for c in [c for c in cats if 'obs.json' in c.name]:
    cat = intake_esm.intake.open_esm_datastore(c)
    options_dict['Datasets_2-Observations'].extend(list(cat.df['title'].unique()))

options_dict['Datasets_3-Reanalysis'] = []
for c in [c for c in cats if 'reanalysis.json' in c.name]:
    cat = intake_esm.intake.open_esm_datastore(c)
    options_dict['Datasets_3-Reanalysis'].extend(list(cat.df['title'].unique()))

options_dict['Datasets_4-forecasts'] = []
for c in [c for c in cats if 'forecast.json' in c.name]:
    cat = intake_esm.intake.open_esm_datastore(c)
    options_dict['Datasets_4-forecasts'].extend(list(cat.df['title'].unique()))

for o in options_dict.keys():
    print(o)
    options1 = options_dict[o]
    title_w = pn.widgets.Select(options=options1)

    lang='en'
    # title_w
    @pn.depends(title_w.param.value)
    def create_data_summary(dataset=title_w.param.value):
        summary_fields = {}
        summary_fields['en'] = dict(title='Summary', dataset='dataset',tutorial='tutorial', location='location',
                                    filename='filename', project= 'project (processing level)', frequency='frequency',
                                    temporal_coverage='temporal coverage', variables='variables',
                                    driving_experiment='driving experiment(s)'
                                    )
        summary_fields['fr'] = dict(title='Sommaire', dataset='jeu de données', tutorial='tutoriel', location='emplacement',
                                    filename='nom de fichier',project='projet (niveau de traitement)', frequency='fréquence',
                                    temporal_coverage='couverture temporelle', variables='variables',
                                    driving_experiment='expérience(s) de pilotage'
                                    )
        details_fields = {}
        details_fields['en'] = dict(title='Details', more_info='more info', abstract='abstract')
        details_fields['fr'] = dict(title='Détails', more_info="plus d'info", abstract='résumé')

        legal_fields = {}
        legal_fields['en'] = dict(title='License / Terms of use', license_type='license type', license='license')
        legal_fields['fr'] = dict(title='Licence / Conditions', license_type='type de licence', license='licence')
        df = None
        for c in cats:
            cat = intake_esm.intake.open_esm_datastore(c)
            if len(cat.search(title=dataset).df) > 0:
                df = cat.search(title=dataset).df
                break

        ds = xr.open_dataset(df['path'][0], chunks=dict(time=1))
        if 'longitude' in ds.dims:
            ds = ds.rename({'longitude':'lon'})
        if 'latitude' in ds.dims:
            ds = ds.rename({'latitude': 'lat'})
        if 'member' in ds.dims:
            ds = ds.isel(member=0)
        if np.all(ds.lon.values >= 0):
            lons = ds.lon.values
            lons[lons >= 180] = lons[lons >= 180] - 360
            ds = ds.assign_coords(lon=lons)
        if 'realization' in ds.dims:
            ds = ds.isel(realization=0).squeeze()
        if set(['lat', 'lon']).issubset(set(list(ds.dims.keys()))):
            ds = ds.sortby(['lat', 'lon'])
        xlim = (float(ds.lon.min().values), float(ds.lon.max().values))

        ylim = (float(ds.lat.min().values), float(ds.lat.max().values))

        polygon = Polygon([(xlim[0], ylim[0]), (xlim[0], ylim[1]), (xlim[1], ylim[1]), (xlim[1], ylim[0]), (xlim[0], ylim[0])])
        poly_gdf = gpd.GeoDataFrame([1], geometry=[polygon], crs=world.crs)
        try:
            world1 = gpd.clip(world, poly_gdf)
        except:
            world1 = world.copy()
        lic = ds.attrs['license']

        # bias corr specific info
        if 'driving_experiment' in df.columns:
            exp1 = [d.split(',') for d in df['driving_experiment'].unique()]
            exp1 = sorted(list({x for l in exp1 for x in l}))
        else:
            exp1 = None
        if 'project_id' in df.columns and 'processing' in df.columns:
            prj1 = f"{df['project_id'].unique()[0]} ({df['processing'].unique()[0]})"
        else:
            prj1 = None

        w = 175

        ## summary info
        thrds_access = f"https://{'/'.join([p for p in df['path'][0].split('//')[-1].split('/')[0:-1]])}/catalog.html".replace(
            'dodsC', 'catalog')
        if len(df['path']) == 1:
            ncmls = df['path'][0].split('//')[-1].split('/')[-1]
        else:

            ncmls = f"ensemble of {len(df['path'])} files"



        summary = pn.Column(pn.Row(pn.pane.HTML(f"{summary_fields[lang]['dataset']} :",),pn.pane.HTML(f'{dataset}',)))

        summary.append(pn.Row(pn.pane.HTML(f"{summary_fields[lang]['tutorial']} :",),pn.pane.HTML(f'<a href="/climate_analysis.html" target="_blank">PAVICS data access tutorial<a />',)))


        summary.append(pn.Row(pn.pane.HTML(f"{summary_fields[lang]['location']} ({summary_fields[lang]['filename']}):", ),
                              pn.pane.HTML(f'<a href="{thrds_access}" target="_blank">THREDDS catalog<a />' + f" ({ncmls})")))


        inst_field = 'institution' if 'institution' in df.columns else 'institute'

        summary.append(pn.Row(pn.pane.HTML("institution :"), pn.pane.HTML(df[inst_field].unique()[0])))

        if prj1:
            summary.append(pn.Row(pn.pane.HTML(f"{summary_fields[lang]['project']} :", ), pn.pane.HTML(prj1)))
        if 'frequency' in df.columns:
            summary.append(pn.Row(pn.pane.HTML(f"{summary_fields[lang]['frequency']} :", ), pn.pane.HTML(df['frequency'].unique()[0])))
        if o == 'Datasets_4-forecasts':
            summary.append(pn.Row(pn.pane.HTML(f"{summary_fields[lang]['temporal_coverage']} :", ), pn.pane.HTML(
                f"current forecast")))
        else:
            summary.append(pn.Row(pn.pane.HTML(f"{summary_fields[lang]['temporal_coverage']} :", ), pn.pane.HTML(
            f"{ds.time.min().dt.strftime('%Y/%m/%d').values} - {ds.time.max().dt.strftime('%Y/%m/%d').values}")))

        if 'Climatedata.ca' not in dataset:
            summary.append(
                pn.Row(pn.pane.HTML(f"{summary_fields[lang]['variables']} :", ), pn.pane.HTML(', '.join(sorted([v for v in ds.data_vars])))))
        if exp1:
            summary.append(pn.Row(pn.pane.HTML(f"{summary_fields[lang]['driving_experiment']} :",), pn.pane.HTML(', '.join(exp1))))

        out = pn.Tabs((summary_fields[lang]['title'], summary))

        ## details

        details = pn.Column(pn.Row(pn.pane.HTML(f"{details_fields[lang]['abstract']} : ", width=w), pn.pane.HTML(ds.attrs['abstract'],)))
        for check in ['bias_adjust', 'target_data', 'target_ref']:
            for attr in [attr for attr in ds.attrs if check in attr]:
                details.append(pn.Row(pn.pane.HTML(f"{attr.replace('_', ' ')}: ", ),
                                      pn.pane.HTML(ds.attrs[attr], )))


        details.append(pn.Row(pn.pane.HTML(f"{details_fields[lang]['more_info']} : ", width=w), pn.pane.HTML(ds.attrs['dataset_description'], )))
        out.append((details_fields[lang]['title'], details))


        ## legal

        legal = pn.Column(
            pn.Row(pn.pane.HTML(f"{legal_fields[lang]['license_type']} :", ), pn.pane.HTML(ds.attrs['license_type'], )))
        legal.append(pn.Row(pn.pane.HTML(f"{legal_fields[lang]['license']} :",), pn.pane.HTML(ds.attrs['license'], )))

        for check in ['attribution', 'citation', 'terms']:
            for attr in [attr for attr in ds.attrs if check in attr]:
                attr_name = attr.replace('_',' ')
                if lang == 'fr':
                    attr_name = attr_name.replace("terms of use", "conditions d'utilisation")
                legal.append(pn.Row(pn.pane.HTML(f"{attr_name}: ", ),
                                    pn.pane.HTML(ds.attrs[attr], )))

        out.append((legal_fields[lang]['title'], legal))

        ## map

        if set(['lat', 'lon']).issubset(set(list(ds.dims.keys()))) or set(['rlat', 'rlon']).issubset(set(list(ds.dims.keys()))):

            v = sorted(list(ds.data_vars.keys()), reverse=True)
            for vv in v:
                if len(ds[vv].dims) >=3:
                    break
            if units.units2pint(ds[vv]) == 'kelvin':
                unit_str = '°K'
            else:
                unit_str = units.pint2cfunits(units.units2pint(ds[vv]))
            title = {}
            title['en'] = f"Example of spatial domain : single time-step for variable {vv} ({unit_str})"
            title['fr'] = f"Exemple de domaine spatial: pas de temps unique pour variable {vv} ({unit_str})"
            if set(['lat', 'lon']).issubset(set(list(ds.dims.keys()))):
                map1 = ds[vv].isel(time=0).hvplot.image(title=title[lang],x='lon',y='lat',xlim=xlim, ylim=ylim, rasterize=True, cmap='RdBu_r', hover=False,
                                                      xlabel='longitude',ylabel='latitude',
                                                      frame_height=300, frame_width=750).opts(toolbar=None, fontsize={'title': 12} ) * world1.hvplot(c='')
            else:
                map1 = ds[vv].isel(time=0).hvplot.contourf(levels=15,title=title[lang], x='lon', y='lat', xlim=xlim, ylim=ylim, rasterize=True,
                                                    cmap='RdBu_r', hover=False, xlabel = 'longitude', ylabel = 'latitude',
                                                    frame_height = 300, frame_width = 750).opts(toolbar=None, fontsize={'title': 12} ) * world1.hvplot(c='')

        else:
            vars = list(ds.data_vars)
            vars.remove('lat')
            vars.remove('lon')
            df1 = ds.drop_vars(vars).isel(time=0).to_dataframe()

            map1 = world1.hvplot(c='') * df1.hvplot.points('lon', 'lat', xlim=xlim, ylim=ylim,
                                                          hover_cols=['station', 'station_name'], frame_height=300,
                                                          frame_width=750)

        out1 = pn.Column(map1, out)
        return out1


    MAX_WIDTH = 800

    pn.config.sizing_mode = "stretch_width"

    spacer = pn.Spacer(height=0, margin=0)
    #link = pn.pane.HTML(f'<a href="/climate_analysis.html" target="_blank">PAVICS data access tutorial<a />')
    del lang
    for lang in ['fr','en']:
        main_content = pn.Column(title_w, create_data_summary, sizing_mode="stretch_width",
                                 max_width=MAX_WIDTH, align="center")

        main_area = pn.Column(
            spacer,  # TRICK: WONT WORK WITHOUT. YOU CAN SET HEIGHT TO 0 TO NOT TAKE UP HEIGHT
            main_content,
            sizing_mode="stretch_both",
        )
        from bokeh.resources import CDN
        outhtml = f'{o}.html'
        if lang == 'fr':
            outhtml = f'{o}_{lang}.html'
        main_area.save(outhtml, embed=True, resources=CDN)
        outdir =  repo.joinpath('src/assets/notebooks')
        shutil.copy(outhtml, outdir.as_posix())
