import bpy
import math
from mathutils import Vector


from data_vis.utils.data_utils import get_data_as_ll, find_data_range, normalize_value, find_axis_range
from data_vis.utils.color_utils import ColorGen
from data_vis.general import OBJECT_OT_GenericChart, DV_LabelPropertyGroup, DV_ColorPropertyGroup, DV_AxisPropertyGroup
from data_vis.operators.features.axis import AxisFactory
from data_vis.data_manager import DataManager, DataType
from data_vis.colors import NodeShader


class OBJECT_OT_BarChart(OBJECT_OT_GenericChart):
    '''Creates Bar Chart, supports 2D and 3D Numerical Data and 2D categorical data with or w/o labels'''
    bl_idname = 'object.create_bar_chart'
    bl_label = 'Bar Chart'
    bl_options = {'REGISTER', 'UNDO'}

    dimensions: bpy.props.EnumProperty(
        name='Dimensions',
        items=(
            ('3', '3D', 'X, Y, Z'),
            ('2', '2D', 'X, Z'),
        )
    )

    data_type: bpy.props.EnumProperty(
        name='Chart type',
        items=(
            ('0', 'Numerical', 'X relative to Z or Y'),
            ('1', 'Categorical', 'Label and value'),
        )
    )

    bar_size: bpy.props.FloatVectorProperty(
        name='Bar size',
        size=2,
        default=(0.05, 0.05)
    )

    axis_settings: bpy.props.PointerProperty(
        type=DV_AxisPropertyGroup
    )

    color_settings: bpy.props.PointerProperty(
        type=DV_ColorPropertyGroup
    )

    label_settings: bpy.props.PointerProperty(
        type=DV_LabelPropertyGroup
    )

    @classmethod
    def poll(cls, context):
        return True
        dm = DataManager()
        return dm.is_type(DataType.Numerical, 3) or dm.is_type(DataType.Categorical, 2)

    def draw(self, context):
        super().draw(context)
        layout = self.layout
        row = layout.row()
        row.prop(self, 'bar_size')

    def init_range(self, data):
        self.axis_settings.x_range = find_axis_range(data, 0)
        self.axis_settings.y_range = find_axis_range(data, 1)

    def data_type_as_enum(self):
        if self.data_type == '0':
            return DataType.Numerical
        elif self.data_type == '1':
            return DataType.Categorical

    def execute(self, context):
        self.init_data()
        if self.data_type_as_enum() == DataType.Numerical:
            if self.axis_settings.auto_ranges:
                self.init_range(self.data)
        else:
            self.dimensions = '2'
            self.axis_settings.x_range[0] = 0
            self.axis_settings.x_range[1] = len(self.data) - 1

        if self.dimensions == '3' and len(self.data[0]) != 3:
            self.report({'ERROR'}, 'Data are only 2D!')
            return {'CANCELLED'}
        tick_labels = []
        self.create_container()
        if self.data_type_as_enum() == DataType.Numerical:
            try:
                data_min, data_max = find_data_range(self.data, self.axis_settings.x_range, self.axis_settings.y_range if self.dimensions == '3' else None)
            except Exception as e:
                self.report({'ERROR'}, 'Cannot find data in this range!')
                return {'CANCELLED'}
        else:
            data_min = min(self.data, key=lambda val: val[1])[1]
            data_max = max(self.data, key=lambda val: val[1])[1]

        #color_gen = ColorGen(self.color_shade, (data_min, data_max))
        shader = NodeShader(self.color_settings.color_shade, NodeShader.Type.str_to_type(self.color_settings.color_type), 2.0, self.chart_origin[2])

        if self.dimensions == '2':
            value_index = 1
        else:
            value_index = 2

        for i, entry in enumerate(self.data):
            if not self.in_axis_range_bounds_new(entry):
                continue

            bpy.ops.mesh.primitive_cube_add()
            bar_obj = context.active_object
            if self.data_type_as_enum() == DataType.Numerical:
                x_value = entry[0]
            else:
                tick_labels.append(entry[0])
                x_value = i
            x_norm = normalize_value(x_value, self.axis_settings.x_range[0], self.axis_settings.x_range[1])

            z_norm = normalize_value(entry[value_index], data_min, data_max)
            if z_norm >= 0.0 and z_norm <= 0.0001:
                z_norm = 0.0001
            if self.dimensions == '2':
                bar_obj.scale = (self.bar_size[0], self.bar_size[1], z_norm * 0.5)
                bar_obj.location = (x_norm, 0.0, z_norm * 0.5)
            else:
                y_norm = normalize_value(entry[1], self.axis_settings.y_range[0], self.axis_settings.y_range[1])
                bar_obj.scale = (self.bar_size[0], self.bar_size[1], z_norm * 0.5)
                bar_obj.location = (x_norm, y_norm, z_norm * 0.5)
        
            bar_obj.data.materials.append(shader.material)
            bar_obj.active_material = shader.material  # self.new_mat(color_gen.next(entry[value_index]), 1)
            bar_obj.parent = self.container_object

        AxisFactory.create(
            self.container_object,
            (self.axis_settings.x_step, self.axis_settings.y_step, self.axis_settings.z_step),
            (self.axis_settings.x_range, self.axis_settings.y_range, (data_min, data_max)),
            int(self.dimensions),
            tick_labels=(tick_labels, [], []),
            labels=self.labels,
            padding=self.axis_settings.padding,
            auto_steps=self.axis_settings.auto_steps,
            offset=0.0
        )

        return {'FINISHED'}
