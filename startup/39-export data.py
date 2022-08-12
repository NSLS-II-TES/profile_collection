import numpy as np
import pandas as pd
import datetime
import tifffile


def export_xy_fly(scanID = -1):
    start = db[scanID].start
    dt = datetime.datetime.fromtimestamp(start["time"])
    filepath = os.path.expanduser(
        f"~/Users/Data/{start['operator']}/{dt.date().isoformat()}/xy_fly/"
        f"{start['scan_title']}-{start['scan_id']}-{start['operator']}-{dt.time().isoformat()}.log"
    )
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "wt") as output_file:
        output_file.write(pprint.pformat(start))
    # Save to Lustre
    filepath = os.path.expanduser(
        f"/nsls2/data/tes/legacy/usersdata/Data/{start['operator']}/{dt.date().isoformat()}/xy_fly/"
        f"{start['scan_title']}-{start['scan_id']}-{start['operator']}-{dt.time().isoformat()}.log"
    )
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "wt") as output_file:
        output_file.write(pprint.pformat(start))

def export_E_fly(scanID=-1):
    h = db[scanID]
    start = h.start
    element = start['user_input']['element']
    roi = rois(element)
    d = np.array(list(h.data('fluor', stream_name='primary', fill=True)))
    If = np.sum(d[:, :, :, roi[0]:roi[1]], axis=-1)
    I_Trans_TEY = h.table()['fbratio']
    E = h.table('energy_bins')['E_centers'][1]
    I0 = h.table()['I0']
    I_sclr_S = h.table()['S']
    Dwell_time = h.table()['dwell_time']
    dt = datetime.datetime.fromtimestamp(start["time"])

    file_head = {'beamline_id': 'TES/8-BM of NSLS-II',
                 'operator': start['operator'],
                 'plan_name': start['plan_name'],
                 'scan_id': start['scan_id'],
                 'scan_title': start['scan_title'],
                 'time': f"{dt.date().isoformat()} {dt.time().isoformat()}",
                 'uid': start['uid'],
                 'user_input': start['user_input'],
                 'derived_input': start['derived_input']
                 }

    for ii in range(If.shape[0]):
        if If.shape[2] == 1:
            df = pd.DataFrame({'#Energy': E,
                               'Dwell_time': Dwell_time[ii + 1],
                               'I0': I0[ii + 1],
                               'I_Trans_TEY ':I_Trans_TEY[ii+1],
                               'If_CH1': If[ii, :, 0],
                               'I_sclr_S': I_sclr_S[ii + 1]
                               })
        else:
            df = pd.DataFrame({'#Energy': E,
                               'Dwell_time': Dwell_time[ii + 1],
                               'I0': I0[ii + 1],
                               'I_Trans_TEY ': I_Trans_TEY[ii + 1],
                               'If_CH1': If[ii, :, 0],
                               'If_CH2': If[ii, :, 1],
                               'I_sclr_S': I_sclr_S[ii + 1]
                               })

        filepath = os.path.expanduser(
            f"~/Users/Data/{start['operator']}/{dt.date().isoformat()}/E_fly/"
            f"{start['scan_title']}-{start['scan_id']}-{start['operator']}-{dt.time().strftime('%H-%M-%S')}-{ii}.dat")
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "wt") as output_file:
            output_file.write(pprint.pformat(file_head,width=100))
            output_file.write('\n')
            output_file.write('\n')
            output_file.write('\n')

        df.to_csv(filepath, header=True, index=False, mode='a')
        print(f'Data exported to {filepath}')

        filepath = os.path.expanduser(
            f"/nsls2/data/tes/legacy/usersdata/Data/{start['operator']}/{dt.date().isoformat()}/E_fly/"
            f"{start['scan_title']}-{start['scan_id']}-{start['operator']}-{dt.time().strftime('%H-%M-%S')}-{ii}.dat")
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "wt") as output_file:
            output_file.write(pprint.pformat(file_head,width=100))
            output_file.write('\n')
            output_file.write('\n')
            output_file.write('\n')

        df.to_csv(filepath, header=True, index=False, mode='a')
        print(f'Data exported to {filepath}')

def export_E_step(scanID=-1, scan_iter=0):

    h = db[scanID] # read data from databroker

    e_back = yield from _get_v_with_dflt(mono.e_back, 1977.04)
    energy_cal = yield from _get_v_with_dflt(mono.cal, 0.40118)
    def _linear_to_energy(linear):
        linear = np.asarray(linear)
        return e_back / np.sin(
            np.deg2rad(45)
            + 0.5 * np.arctan((28.2474 - linear) / 35.02333)
            + np.deg2rad(energy_cal) / 2
        )
    E = _linear_to_energy(h.table()['mono_linear'])

    #E = h.table()['mono_energy']
    I0 = h.table()['I0']
    I_Trans_TEY = h.table()['fbratio']
    If_1_roi1 = h.table()['xs_channel1_rois_roi01_value_sum']
    If_1_roi2 = h.table()['xs_channel1_rois_roi02_value_sum']
    If_1_roi3 = h.table()['xs_channel1_rois_roi03_value_sum']
    If_1_roi4 = h.table()['xs_channel1_rois_roi04_value_sum']
    #If_2_roi1 = h.table()['xs_channel2_rois_roi01_value_sum']
    #If_2_roi2 = h.table()['xs_channel2_rois_roi02_value_sum']
    #If_2_roi3 = h.table()['xs_channel2_rois_roi03_value_sum']
    #If_2_roi4 = h.table()['xs_channel2_rois_roi04_value_sum']

    #df = pd.DataFrame({'#Energy': E, 'I0': I0, 'I_TEY':I_TEY,
    #                   'If_CH1_roi1': If_1_roi1, 'If_CH1_roi2': If_1_roi2, 'If_CH1_roi3':If_1_roi3, 'If_CH1_roi4': If_1_roi4,
    #                   'If_CH2_roi1': If_2_roi1, 'If_CH2_roi2': If_2_roi2, 'If_CH2_roi3':If_2_roi3, 'If_CH2_roi4': If_2_roi4})
    df = pd.DataFrame({'#Energy': E, 'I0': I0, 'I_Trans_TEY': I_Trans_TEY,
                       'If_CH1_roi1': If_1_roi1, 'If_CH1_roi2': If_1_roi2, 'If_CH1_roi3': If_1_roi3,
                       'If_CH1_roi4': If_1_roi4})
    #df['#Energy'] = df1['#Energy'].str.rjust(13, " ")

    start = h.start
    dt = datetime.datetime.fromtimestamp(start["time"])

    file_head ={'beamline_id': 'TES/8-BM of NSLS-II',
     'operator': start['operator'],
     'plan_name': start['plan_name'],
     'scan_id': start['scan_id'],
     'scan_title': start['scan_title'],
     'time': f"{dt.date().isoformat()} {dt.time().isoformat()}",
     'uid': start['uid'],
     'user_input': start['user_input'],
     'derived_input': start['derived_input']
                }

    filepath = os.path.expanduser(
        f"~/Users/Data/{start['operator']}/{dt.date().isoformat()}/E_step/"
        f"{start['scan_title']}-{start['scan_id']}-{start['operator']}-{dt.time().strftime('%H-%M-%S')}-{scan_iter}.cvs")
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, "wt") as output_file:
        output_file.write(pprint.pformat(file_head,width=100))
        output_file.write('\n')
        output_file.write('\n')
        output_file.write('\n')

    df.to_csv(filepath, header = True,index = False,mode='a')
    print(f'Data exported to {filepath}')
    # Save to Lustre
    filepath = os.path.expanduser(
        f"/nsls2/data/tes/legacy/usersdata/Data/{start['operator']}/{dt.date().isoformat()}/E_step/"
        f"{start['scan_title']}-{start['scan_id']}-{start['operator']}-{dt.time().strftime('%H-%M-%S')}-{scan_iter}.cvs")
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, "wt") as output_file:
        output_file.write(pprint.pformat(file_head,width=100))
        output_file.write('\n')
        output_file.write('\n')
        output_file.write('\n')

    df.to_csv(filepath, header = True,index = False,mode='a')
    print(f'Data exported to {filepath}')

def tes_data(scanID = -1,scan_iter = 0):
    h = db[scanID]
    start = h.start
    if start['plan_name'] == 'E_fly' or start['plan_name'] == 'Batch_E_fly':
        export_E_fly(scanID)
    elif start['plan_name'] == 'list_scan':
        export_E_step(scanID,scan_iter)
    else:
        print(f"Plan_name is {start['plan_name']}.")


def export_xy_fly_sclr(scanID = -1):
    h = db[scanID]
    names = ["I0","x_centers", "y_centers","S","Mg","Sr_Si", "Al", "P", "Ca" ]
    # read data from databroker
    for name in names:
        fln = f"{name}.tiff"
        arr = np.vstack(h.table()[name])
        tifffile.imsave(fln, arr.astype(np.float32), imagej=True)

    names_norm = ["S", "Mg", "Sr_Si", "Al", "P", "Ca"]
    for name in names_norm:
        fln = f"{name}+'_norm'.tiff"
        arr = np.vstack(h.table()[name])
        tifffile.imsave(fln, arr.astype(np.float32), imagej=True)


    I0 = h.table()['I0']
    x_centers = h.table()['x_centers']
    y_centers = h.table()['y_centers']
    S = h.table()['S']
    Mg = h.table()['Mg']
    I0 = h.table()['I0']


'''
def ResaveSclr(element, scan_title, scanID, operator):

    h = db[scanID]
    start = db[scanID].start
    If = h.table()[element]
    E = h.table('energy_bins')['E_centers'][1]

    I0 = h.table()['I0']
    Dwell_time = h.table()['dwell_time']

    dt = datetime.datetime.fromtimestamp(start["time"])

    for ii in range(If.shape[0]):
        df = pd.DataFrame({'#Energy': E,
                           'Dwell_time': Dwell_time[ii + 1],
                           'I0': I0[ii + 1],
                           'If': If[ii + 1]})
        filepath = os.path.expanduser(
            f"~/Users/Data/{start['operator']}/{dt.date().isoformat()}/xy_fly/"
            f"{start['scan_title']}-{start['scan_id']}-{start['operator']}-{dt.time().isoformat()}-{ii}.dat")
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        df.to_csv(filepath)

         names = ["S", "x_centers", "y_centers"]
for name in names:       
fln = f"{name}.tiff"       
arr = np.vstack(h.table()[name])       
tifffile.imsave(fln, arr.astype(np.float32), imagej=True)





'''
