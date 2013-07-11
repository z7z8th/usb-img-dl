from const_vars import *
import mtd_part_alloc

type_call_dict = dict()
def update_type_call_dict():
    global type_call_dict
    type_call_dict = {
        IMG_BAREBOX : {'std_name':"barebox",   'name_pattern':r'barebox',
                       'img_type':'dyn_id', 'func_params':(ID_BAREBOX,)},

        IMG_BOOTIMG : {'std_name':'boot',          'name_pattern':r'boot',
                       'img_type':'raw',
                       'func_params':(mtd_part_alloc.BOOTIMG_OFFSET,
                                            mtd_part_alloc.BOOTIMG_LENGTH)},

        IMG_RECOVERY : {'std_name':'recovery',      'name_pattern':r'recovery',
                        'img_type':'raw',
                        'func_params':(mtd_part_alloc.RECOVERY_OFFSET,
                                            mtd_part_alloc.RECOVERY_LENGTH)},

        IMG_SYSTEM : {'std_name':'system',        'name_pattern':r'system',
                      'img_type':'yaffs2',
                      'func_params':(mtd_part_alloc.SYSTEM_OFFSET,
                                            mtd_part_alloc.SYSTEM_LENGTH)},

        IMG_MODEM : {'std_name':'modem-ecos-ps', 'name_pattern':r'modem|ecos',
                     'img_type':'raw',
                     'func_params':(mtd_part_alloc.PS_MODEM_OFFSET,
                                            mtd_part_alloc.PS_MODEM_LENGTH)},

        IMG_ICON : {'std_name':'charging-icon', 'name_pattern':r'lcm|icon',
                    'img_type':'dyn_id', 'func_params':(ID_ICON,)},

        IMG_USER_DATA : {'std_name':'userdata',
                         'name_pattern':r'udata|userdata',
                         'img_type':'yaffs2',
                         'func_params':(mtd_part_alloc.UDATA_OFFSET,
                                            mtd_part_alloc.UDATA_LENGTH)},

        IMG_CACHE: {'std_name':'cache',         'name_pattern':r'cache',
                    'img_type':'raw',  'func_params':(mtd_part_alloc.CACHE_OFFSET,
                                            mtd_part_alloc.CACHE_LENGTH)},

        IMG_M_DATA : {'std_name':'machine-data',
                      'name_pattern':r'mdata|macine-data',
                      'img_type':'yaffs2',
                      'func_params':(mtd_part_alloc.MDATA_OFFSET,
                                            mtd_part_alloc.MDATA_LENGTH)},

        IMG_IMEI : {'std_name':'IMEI-data',     'name_pattern':r'imei',
                    'img_type':'dyn_id', 'func_params':(ID_IMEI,)},

        IMG_BAREBOX_ENV : {'std_name':'barebox-data',
                           'name_pattern':r'barebox-data',
                           'img_type':'dyn_id', 'func_params':(ID_BAREBOX_ENV,)},

        IMG_LDR_APP : {'std_name':'ram-loader',
                       'name_pattern':r'ram_ldr|ldr_app|ram_loader',
                       'img_type':'dyn_id', 'func_params':(ID_LDR_APP,)},
        }


update_type_call_dict()
