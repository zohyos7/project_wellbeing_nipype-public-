import os, sys
from os.path import join as opj
from nipype import Workflow, Node, MapNode
from nipype.interfaces.ants import ApplyTransforms
from nipype.interfaces.utility import IdentityInterface
from nipype.interfaces.io import SelectFiles, DataSink
from nipype.interfaces.fsl import Info

# set dir
experiment_dir = '/data/wellbeing_analysis'
output_dir = 'datasink'
working_dir = 'workingdir'

# task name
task_list = ['empathy']

# Smoothing withds used during normalization
fwhm = [4, 8]

# MNI template
template = '/home/zohyos7/fmri/mni_icbm152_nlin_asym_09c/1mm_T1.nii.gz'


if __name__ == '__main__':
    if len(sys.argv) == 1:
        raise RuntimeError('Should pass subject IDs.')
    
    subject_list = sys.argv[1:]
    
    # Apply Transformation Node
    apply_norm_bold = MapNode(ApplyTransforms(args='--float',
                                        input_image_type=3,
                                        interpolation='BSpline',
                                        invert_transform_flags=[False],
                                        num_threads=8,
                                        reference_image=template,
                                        terminal_output='file'),
                        name='apply_norm_bold', iterfield=['input_image'])

    apply_norm_anat = MapNode(ApplyTransforms(args='--float',
                                        input_image_type=3,
                                        interpolation='BSpline',
                                        invert_transform_flags=[False],
                                        num_threads=8,
                                        reference_image=template,
                                        terminal_output='file'),
                        name='apply_norm_anat', iterfield=['input_image'])

    #subject list
    # subject_list_done_reg = os.listdir("/data/wellbeing_analysis/datasink/antsreg")
    # subject_list_done_reg = [sub[-4:] for sub in subject_list_done_reg]
    # subject_list_done_reg

    # subject_list_done_norm = os.listdir("/data/wellbeing_analysis/datasink/antsflow")
    # subject_list_done_norm = [sub[-4:] for sub in subject_list_done_norm]
    # subject_list_done_norm.sort()

    # full_subject_list = os.listdir("/data/wellbeing_bids")
    # full_subject_list.remove('dataset_description.json')
    # full_subject_list = [sub[-4:] for sub in full_subject_list]
    # full_subject_list.sort()

    # subject_list = list(set(subject_list_done_reg)^set(subject_list_done_norm))

    # Set up Nodes for Normalization
    # Infosource - a function free node to iterate over the list of subject names
    infosource = Node(IdentityInterface(fields=['subject_id', 'task_name','fwhm_id']),
                    name="infosource")
    infosource.iterables = [('subject_id', subject_list),
                            ('task_name', task_list),
                            ('fwhm_id', fwhm)]

    # SelectFiles - to grab the data (alternativ to DataGrabber)
    templates = {'bold': opj('/data/wellbeing_analysis/datasink/preproc', 'sub-{subject_id}', 'task-{task_name}',
                            'fwhm-{fwhm_id}_sasub-{subject_id}_task-{task_name}_bold.nii'),
                'anat': opj('/data/wellbeing_analysis/datasink/preproc', 'sub-{subject_id}', 'task-{task_name}', 
                            'sub-{subject_id}_T1w_brain.nii.gz'),
                'transform': opj('/data/wellbeing_analysis/datasink/antsreg', 'sub-{subject_id}', 'transformComposite.h5')}

    selectfiles = Node(SelectFiles(templates,
                                base_directory=experiment_dir,
                                sort_filelist=True),
                    name="selectfiles")

    # Datasink - creates output folder for important outputs
    datasink = Node(DataSink(base_directory=experiment_dir,
                            container=output_dir),
                    name="datasink")

    # Use the following DataSink output substitutions
    substitutions = [('_fwhm_id_%s_subject_id_%s_task_name_empathy/_apply_norm_anat0' % (f, sub),
                    'sub-%s/anat/' % (sub))
                    for f in fwhm
                    for sub in subject_list]
    subjFolders = [('_fwhm_id_%s_subject_id_%s_task_name_empathy/_apply_norm_bold0'  % (f, sub),
                    'sub-%s/bold/task-empathy/' % (sub))
                for f in fwhm
                for sub in subject_list]

    substitutions.extend(subjFolders)
    datasink.inputs.substitutions = substitutions

    # Initiation of the ANTs normalization workflow
    antsflow = Workflow(name='antsflow')
    antsflow.base_dir = opj(experiment_dir, working_dir)

    # Connect up the ANTs normalization components
    antsflow.connect([(infosource, selectfiles, [('subject_id', 'subject_id'),
                                                ('task_name', 'task_name'),
                                                ('fwhm_id', 'fwhm_id')]),
                    (selectfiles, apply_norm_anat, [('anat', 'input_image'),
                                                ('transform', 'transforms')]),
                    (selectfiles, apply_norm_bold, [('bold', 'input_image'),
                                                    ('transform', 'transforms')]),
                    (apply_norm_anat, datasink, [('output_image', 'antsflow.@anat')]),
                    (apply_norm_bold, datasink, [('output_image', 'antsflow.@bold')])
                    ])

    #while subject_list_done_norm != full_subject_list:
    #    subject_list = subject_list[:5]
    #    antsflow.run('MultiProc', plugin_args={'n_procs': 5})
    #    subject_list_done_norm = os.listdir("/data/wellbeing_analysis/datasink/antsflow")
    #    subject_list_done_norm = [sub[-4:] for sub in subject_list_done_norm]
    #    subject_list_done_norm.sort()
    #    subject_list = list(set(full_subject_list)^set(subject_list_done_norm))

    print("working well")
    antsflow.run('MultiProc', plugin_args={'n_procs': len(subject_list)*3})