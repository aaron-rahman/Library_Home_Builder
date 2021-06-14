import bpy
import time
import math
from os import path
from ..pc_lib import pc_types, pc_unit, pc_utils

from . import common_prompts
from . import data_closet_parts
from .. import home_builder_utils
from .. import home_builder_pointers

class Closet_Starter(pc_types.Assembly):
    show_in_library = True
    category_name = "CLOSETS"
    subcategory_name = "FLOOR_PANELS"

    panel_height = 0
    is_hanging = False
    opening_qty = 4
    panels = []
    left_bridge_parts = []
    right_bridge_parts = []

    def __init__(self,obj_bp=None):
        super().__init__(obj_bp=obj_bp)  
        self.left_bridge_parts = []
        if obj_bp:
            for child in obj_bp.children:
                if "IS_LEFT_BRIDGE_BP" in child:
                    self.left_bridge_parts.append(pc_types.Assembly(child))
                if "IS_RIGHT_BRIDGE_BP" in child:
                    self.right_bridge_parts.append(pc_types.Assembly(child))

            for i in range(1,9):
                opening_height_prompt = self.get_prompt("Opening " + str(i) + " Height")
                if not opening_height_prompt:
                    self.opening_qty = i - 1
                    break

    def add_opening_prompts(self):
        width = self.obj_x.pyclone.get_var('location.x','width')
        p_thickness = self.get_prompt("Panel Thickness").get_var("p_thickness")

        calc_distance_obj = self.add_empty('Calc Distance Obj')
        calc_distance_obj.empty_display_size = .001
        opening_calculator = self.obj_prompts.pyclone.add_calculator("Opening Calculator",calc_distance_obj)

        calc_formula = 'width-p_thickness*' + str(self.opening_qty+1)
        calc_vars = [width,p_thickness]

        for i in range(1,self.opening_qty+1):
            opening_calculator.add_calculator_prompt('Opening ' + str(i) + ' Width')
            self.add_prompt("Opening " + str(i) + " Height",'DISTANCE',pc_unit.millimeter(1523) if self.is_hanging else self.obj_z.location.z)
            self.add_prompt("Opening " + str(i) + " Depth",'DISTANCE',math.fabs(self.obj_y.location.y))
            self.add_prompt("Opening " + str(i) + " Floor Mounted",'CHECKBOX',False if self.is_hanging else True)
            self.add_prompt("Remove Bottom " + str(i),'CHECKBOX',True if self.is_hanging else False)
            if i != self.opening_qty:
                double_panel = self.add_prompt("Double Panel " + str(i),'CHECKBOX',False)
                d_panel = double_panel.get_var('d_panel_' + str(i))
                calc_vars.append(d_panel)
                calc_formula += "-IF(d_panel_" + str(i) + ",p_thickness,0)"

        opening_calculator.set_total_distance(calc_formula,calc_vars)

    def add_panel(self,index,previous_panel):
        previous_panel_x = previous_panel.obj_bp.pyclone.get_var('location.x',"previous_panel_x")

        height = self.obj_z.pyclone.get_var('location.z','height')
        opening_width_prompt = self.get_prompt("Opening " + str(index) + " Width")
        opening_width = opening_width_prompt.get_var("Opening Calculator","opening_width")
        opening_depth = self.get_prompt("Opening " + str(index) + " Depth").get_var('opening_depth')
        opening_height = self.get_prompt("Opening " + str(index) + " Height").get_var('opening_height')
        floor = self.get_prompt("Opening " + str(index) + " Floor Mounted").get_var('floor')
        next_floor = self.get_prompt("Opening " + str(index+1) + " Floor Mounted").get_var('next_floor')
        next_depth = self.get_prompt("Opening " + str(index+1) + " Depth").get_var('next_depth')
        next_height = self.get_prompt("Opening " + str(index+1) + " Height").get_var('next_height')
        dp = self.get_prompt("Double Panel " + str(index)).get_var('dp')
        left_filler = self.get_prompt("Left Side Wall Filler").get_var("left_filler")
        depth = self.obj_y.pyclone.get_var('location.y','depth')
        p_thickness = self.get_prompt("Panel Thickness").get_var("p_thickness")

        panel = data_closet_parts.add_closet_part(self)
        panel.obj_bp["IS_PANEL_BP"] = True
        panel.set_name('Panel ' + str(index))
        panel.loc_x('previous_panel_x+opening_width+p_thickness+IF(dp,p_thickness,0)',[previous_panel_x,opening_width,p_thickness,dp])
        panel.loc_y(value = 0)
        panel.loc_z("IF(dp,IF(next_floor,0,height-next_height),IF(OR(floor,next_floor),0,min(height-opening_height,height-next_height)))",
                    [dp,floor,next_floor,height,opening_height,next_height])        
        panel.rot_y(value=math.radians(-90))
        panel.rot_z(value=0)
        panel.dim_x('IF(dp,next_height,max(IF(floor,opening_height,IF(next_floor,height,opening_height)),IF(next_floor,next_height,IF(floor,height,next_height))))',
                    [floor,height,next_floor,opening_height,next_height,dp])        
        panel.dim_y('IF(dp,-next_depth,-max(opening_depth,next_depth))',[dp,opening_depth,next_depth])
        panel.dim_z('-p_thickness',[p_thickness])

        d_panel = data_closet_parts.add_closet_part(self)
        d_panel.obj_bp["IS_PANEL_BP"] = True
        d_panel.set_name('Double Panel ' + str(index))
        d_panel.loc_x('previous_panel_x+opening_width+p_thickness+p_thickness',[previous_panel_x,opening_width,p_thickness])
        d_panel.loc_y(value = 0)
        d_panel.loc_z("IF(floor,0,height-opening_height)",[floor,height,opening_height])
        d_panel.rot_y(value=math.radians(-90))
        d_panel.rot_z(value=0)
        d_panel.dim_x('opening_height',[opening_height])
        d_panel.dim_y('-opening_depth',[opening_depth])
        d_panel.dim_z('p_thickness',[p_thickness])    
        home_builder_utils.flip_normals(d_panel)
        hide = d_panel.get_prompt('Hide')
        hide.set_formula('IF(dp,False,True)',[dp])

        return panel

    def add_shelf(self,index,left_panel,right_panel):
        left_panel_x = left_panel.obj_bp.pyclone.get_var('location.x','left_panel_x')
        right_panel_x = right_panel.obj_bp.pyclone.get_var('location.x','right_panel_x')

        opening_width = self.get_prompt("Opening " + str(index) + " Width").get_var('Opening Calculator','opening_width')
        opening_depth = self.get_prompt("Opening " + str(index) + " Depth").get_var('opening_depth')
        p_thickness = self.get_prompt("Panel Thickness").get_var("p_thickness")
        s_thickness = self.get_prompt("Shelf Thickness").get_var("s_thickness")

        shelf = data_closet_parts.add_closet_part(self)
        shelf.obj_bp["IS_SHELF_BP"] = True
        shelf.set_name('Shelf ' + str(index))
        shelf.loc_x('left_panel_x+p_thickness',[left_panel_x,p_thickness])
        shelf.loc_y(value = 0)
        shelf.loc_z(value = 0)
        shelf.rot_y(value = 0)
        shelf.rot_z(value = 0)
        shelf.dim_x('opening_width',[opening_width])
        shelf.dim_y('-opening_depth',[opening_depth])
        shelf.dim_z('s_thickness',[s_thickness])
        home_builder_utils.flip_normals(shelf)
        return shelf

    def add_toe_kick(self,index,left_panel,right_panel):
        left_panel_x = left_panel.obj_bp.pyclone.get_var('location.x','left_panel_x')
        right_panel_x = right_panel.obj_bp.pyclone.get_var('location.x','right_panel_x')
        floor = self.get_prompt("Opening " + str(index) + " Floor Mounted").get_var('floor')
        opening_depth = self.get_prompt("Opening " + str(index) + " Depth").get_var('opening_depth')
        opening_width = self.get_prompt("Opening " + str(index) + " Width").get_var('Opening Calculator','opening_width')
        double_panel = self.get_prompt("Double Panel " + str(index))
        remove_bottom = self.get_prompt("Remove Bottom " + str(index)).get_var('remove_bottom')
        p_thickness = self.get_prompt("Panel Thickness").get_var("p_thickness")
        s_thickness = self.get_prompt("Shelf Thickness").get_var("s_thickness")
        kick_height = self.get_prompt("Closet Kick Height").get_var("kick_height")
        kick_setback = self.get_prompt("Closet Kick Setback").get_var("kick_setback")

        kick = data_closet_parts.add_closet_part(self)
        kick.obj_bp["IS_SHELF_BP"] = True
        kick.set_name('Kick ' + str(index))
        kick.loc_x('left_panel_x+p_thickness',[left_panel_x,p_thickness])
        kick.loc_y('-opening_depth+kick_setback',[opening_depth,kick_setback])
        kick.loc_z(value = 0)
        kick.rot_x(value = math.radians(-90))
        kick.rot_y(value = 0)
        kick.rot_z(value = 0)
        kick.dim_x('opening_width',[opening_width])
        kick.dim_y('-kick_height',[kick_height])
        kick.dim_z('s_thickness',[s_thickness])
        hide = kick.get_prompt("Hide")
        hide.set_formula('IF(floor,IF(remove_bottom,True,False),True)',[floor,remove_bottom])
        home_builder_utils.flip_normals(kick)
        return kick

    def add_opening(self,index,left_panel,right_panel):
        left_panel_x = left_panel.obj_bp.pyclone.get_var('location.x','left_panel_x')
        right_panel_x = right_panel.obj_bp.pyclone.get_var('location.x','right_panel_x')

        p_height = self.obj_z.pyclone.get_var('location.z','p_height')
        floor = self.get_prompt("Opening " + str(index) + " Floor Mounted").get_var('floor')
        opening_width = self.get_prompt("Opening " + str(index) + " Width").get_var('Opening Calculator','opening_width')
        opening_depth = self.get_prompt("Opening " + str(index) + " Depth").get_var('opening_depth')
        opening_height = self.get_prompt("Opening " + str(index) + " Height").get_var('opening_height')
        remove_bottom = self.get_prompt("Remove Bottom " + str(index)).get_var('remove_bottom')
        p_thickness = self.get_prompt("Panel Thickness").get_var("p_thickness")
        s_thickness = self.get_prompt("Shelf Thickness").get_var("s_thickness")
        kick_height = self.get_prompt("Closet Kick Height").get_var("kick_height")

        opening = data_closet_parts.add_closet_opening(self)
        opening.set_name('Opening ' + str(index))
        opening.loc_x('left_panel_x+p_thickness',[left_panel_x,p_thickness])
        opening.loc_y('-opening_depth',[opening_depth])
        opening.loc_z('IF(floor,kick_height,p_height-opening_height)+IF(remove_bottom,0,s_thickness)',
                         [floor,kick_height,p_height,opening_height,remove_bottom,s_thickness])
        opening.rot_x(value = 0)
        opening.rot_y(value = 0)
        opening.rot_z(value = 0)
        opening.dim_x('opening_width',[opening_width])
        opening.dim_y('opening_depth',[opening_depth])
        opening.dim_z('opening_height-IF(floor,kick_height,0)-IF(remove_bottom,s_thickness,s_thickness*2)',[opening_height,kick_height,s_thickness,floor,remove_bottom])
        return opening

    def pre_draw(self):
        self.create_assembly()

        self.obj_x.location.x = pc_unit.inch(96)
        self.obj_y.location.y = -pc_unit.inch(12)
        self.obj_z.location.z = pc_unit.millimeter(2131)

        width = self.obj_x.pyclone.get_var('location.x','width')
        height = self.obj_z.pyclone.get_var('location.z','height')
        depth = self.obj_y.pyclone.get_var('location.y','depth')

        reference = data_closet_parts.add_closet_part(self)
        reference.obj_bp["IS_REFERENCE"] = True
        reference.loc_x(value = 0)
        reference.loc_y(value = 0)
        reference.loc_z(value = 0)
        reference.rot_x(value = 0)
        reference.rot_y(value = 0)
        reference.rot_z(value = 0)      
        reference.dim_x('width',[width])
        reference.dim_y('depth',[depth])
        reference.dim_z('height',[height])          

    def add_left_blind_parts(self):
        p_height = self.obj_z.pyclone.get_var('location.z','p_height')
        floor_1 = self.get_prompt("Opening 1 Floor Mounted").get_var("floor_1")
        height_1 = self.get_prompt("Opening 1 Height").get_var("height_1")
        kick_setback = self.get_prompt('Closet Kick Setback').get_var('kick_setback')
        b_left_width = self.get_prompt('Left Bridge Shelf Width').get_var("b_left_width")
        kick_height = self.get_prompt('Closet Kick Height').get_var("kick_height")
        b_left = self.get_prompt('Bridge Left').get_var("b_left")
        s_thickness = self.get_prompt("Shelf Thickness").get_var("s_thickness")
        depth_1 = self.get_prompt("Opening 1 Depth").get_var("depth_1")

        left_bot_bridge = data_closet_parts.add_closet_part(self)
        left_bot_bridge.obj_bp["IS_LEFT_BRIDGE_BP"] = True
        left_bot_bridge.set_name('Left Bridge Bottom')
        left_bot_bridge.loc_x('-b_left_width',[b_left_width])
        left_bot_bridge.loc_y(value = 0)
        left_bot_bridge.loc_z('IF(floor_1,kick_height,p_height-height_1)',[floor_1,kick_height,p_height,height_1])
        left_bot_bridge.rot_y(value = 0)
        left_bot_bridge.rot_z(value = 0)
        left_bot_bridge.dim_x('b_left_width',[b_left_width])
        left_bot_bridge.dim_y('-depth_1',[depth_1])
        left_bot_bridge.dim_z('s_thickness',[s_thickness])
        hide = left_bot_bridge.get_prompt("Hide")
        hide.set_formula('IF(b_left,False,True)',[b_left])
        home_builder_utils.flip_normals(left_bot_bridge)
        self.left_bridge_parts.append(left_bot_bridge)

        left_top_bridge = data_closet_parts.add_closet_part(self)
        left_top_bridge.obj_bp["IS_LEFT_BRIDGE_BP"] = True
        left_top_bridge.set_name('Left Bridge Bottom')
        left_top_bridge.loc_x('-b_left_width',[b_left_width])
        left_top_bridge.loc_y(value = 0)
        left_top_bridge.loc_z('IF(floor_1,height_1,p_height)',[floor_1,height_1,p_height])
        left_top_bridge.rot_y(value = 0)
        left_top_bridge.rot_z(value = 0)
        left_top_bridge.dim_x('b_left_width',[b_left_width])
        left_top_bridge.dim_y('-depth_1',[depth_1])
        left_top_bridge.dim_z('-s_thickness',[s_thickness])
        hide = left_top_bridge.get_prompt("Hide")
        hide.set_formula('IF(b_left,False,True)',[b_left])
        home_builder_utils.flip_normals(left_top_bridge)
        self.left_bridge_parts.append(left_top_bridge)

        left_bridge_kick = data_closet_parts.add_closet_part(self)
        left_bridge_kick.obj_bp["IS_LEFT_BRIDGE_BP"] = True
        left_bridge_kick.set_name('Left Bridge Bottom')
        left_bridge_kick.loc_x('-b_left_width-kick_setback',[b_left_width,kick_setback])
        left_bridge_kick.loc_y('-depth_1+kick_setback',[depth_1,kick_setback])
        left_bridge_kick.loc_z(value = 0)
        left_bridge_kick.rot_x(value = math.radians(-90))
        left_bridge_kick.rot_y(value = 0)
        left_bridge_kick.rot_z(value = 0)
        left_bridge_kick.dim_x('b_left_width+kick_setback',[b_left_width,kick_setback])
        left_bridge_kick.dim_y('-kick_height',[kick_height])
        left_bridge_kick.dim_z('s_thickness',[s_thickness])
        hide = left_bridge_kick.get_prompt("Hide")
        hide.set_formula('IF(b_left,IF(floor_1,False,True),True)',[b_left,floor_1])
        home_builder_utils.flip_normals(left_bridge_kick)
        self.left_bridge_parts.append(left_bridge_kick)

    def add_right_blind_parts(self):
        p_height = self.obj_z.pyclone.get_var('location.z','p_height')
        floor_last = self.get_prompt("Opening " + str(self.opening_qty) + " Floor Mounted").get_var("floor_last")        
        width = self.obj_x.pyclone.get_var('location.x','width')
        height_last = self.get_prompt("Opening " + str(self.opening_qty) + " Height").get_var("height_last")
        kick_setback = self.get_prompt('Closet Kick Setback').get_var('kick_setback')
        b_right_width = self.get_prompt('Right Bridge Shelf Width').get_var("b_right_width")
        kick_height = self.get_prompt('Closet Kick Height').get_var("kick_height")
        b_right = self.get_prompt('Bridge Right').get_var("b_right")
        s_thickness = self.get_prompt("Shelf Thickness").get_var("s_thickness")
        depth_last = self.get_prompt("Opening " + str(self.opening_qty) + " Depth").get_var("depth_last")

        right_bot_bridge = data_closet_parts.add_closet_part(self)
        right_bot_bridge.obj_bp["IS_RIGHT_BRIDGE_BP"] = True
        right_bot_bridge.set_name('Right Bridge Bottom')
        right_bot_bridge.loc_x('width',[width])
        right_bot_bridge.loc_y(value = 0)
        right_bot_bridge.loc_z('IF(floor_last,kick_height,p_height-height_last)',[floor_last,kick_height,p_height,height_last])
        right_bot_bridge.rot_y(value = 0)
        right_bot_bridge.rot_z(value = 0)
        right_bot_bridge.dim_x('b_right_width',[b_right_width])
        right_bot_bridge.dim_y('-depth_last',[depth_last])
        right_bot_bridge.dim_z('s_thickness',[s_thickness])
        hide = right_bot_bridge.get_prompt("Hide")
        hide.set_formula('IF(b_right,False,True)',[b_right])        
        home_builder_utils.flip_normals(right_bot_bridge)
        self.right_bridge_parts.append(right_bot_bridge)

        right_top_bridge = data_closet_parts.add_closet_part(self)
        right_top_bridge.obj_bp["IS_RIGHT_BRIDGE_BP"] = True
        right_top_bridge.set_name('Right Bridge Bottom')
        right_top_bridge.loc_x('width',[width])
        right_top_bridge.loc_y(value = 0)
        right_top_bridge.loc_z('IF(floor_last,height_last,p_height)',[floor_last,height_last,p_height])
        right_top_bridge.rot_y(value = 0)
        right_top_bridge.rot_z(value = 0)
        right_top_bridge.dim_x('b_right_width',[b_right_width])
        right_top_bridge.dim_y('-depth_last',[depth_last])
        right_top_bridge.dim_z('-s_thickness',[s_thickness])
        hide = right_top_bridge.get_prompt("Hide")
        hide.set_formula('IF(b_right,False,True)',[b_right])        
        home_builder_utils.flip_normals(right_top_bridge)
        self.right_bridge_parts.append(right_top_bridge)

        right_bridge_kick = data_closet_parts.add_closet_part(self)
        right_bridge_kick.obj_bp["IS_RIGHT_BRIDGE_BP"] = True
        right_bridge_kick.set_name('Right Bridge Kick')
        right_bridge_kick.loc_x('width',[width])
        right_bridge_kick.loc_y('-depth_last+kick_setback',[depth_last,kick_setback])
        right_bridge_kick.loc_z(value = 0)
        right_bridge_kick.rot_x(value = math.radians(-90))
        right_bridge_kick.rot_y(value = 0)
        right_bridge_kick.rot_z(value = 0)
        right_bridge_kick.dim_x('b_right_width+kick_setback',[b_right_width,kick_setback])
        right_bridge_kick.dim_y('-kick_height',[kick_height])
        right_bridge_kick.dim_z('s_thickness',[s_thickness])
        hide = right_bridge_kick.get_prompt("Hide")
        hide.set_formula('IF(b_right,IF(floor_last,False,True),True)',[b_right,floor_last])  
        home_builder_utils.flip_normals(right_bridge_kick)
        self.right_bridge_parts.append(right_bridge_kick)

    def draw(self):
        self.panels = []
        start_time = time.time()

        self.obj_bp["IS_CLOSET_BP"] = True
        self.obj_bp["PROMPT_ID"] = "home_builder.closet_prompts" 
        self.obj_bp["MENU_ID"] = "HOMEBUILDER_MT_cabinet_menu"
        self.obj_y['IS_MIRROR'] = True

        width = self.obj_x.pyclone.get_var('location.x','width')
        height = self.obj_z.pyclone.get_var('location.z','height')
        depth = self.obj_y.pyclone.get_var('location.y','depth')

        common_prompts.add_closet_thickness_prompts(self)
        panel_thickness_var = self.get_prompt("Panel Thickness").get_var("panel_thickness_var")
        shelf_thickness_var = self.get_prompt("Shelf Thickness").get_var("shelf_thickness_var")        
        closet_kick_height = self.add_prompt("Closet Kick Height",'DISTANCE',pc_unit.inch(2.5)) 

        closet_kick_height_var = closet_kick_height.get_var("closet_kick_height_var")
        closet_kick_setback = self.add_prompt("Closet Kick Setback",'DISTANCE',pc_unit.inch(1.125)) 
        left_end_condition = self.add_prompt("Left End Condition",'COMBOBOX',0,["EP","WP","CP","OFF"]) 
        lec = left_end_condition.get_var("lec")
        right_end_condition = self.add_prompt("Right End Condition",'COMBOBOX',0,["EP","WP","CP","OFF"]) 
        rec = right_end_condition.get_var("rec")
        left_side_wall_filler = self.add_prompt("Left Side Wall Filler",'DISTANCE',0) 
        left_filler = left_side_wall_filler.get_var("left_filler")
        right_side_wall_filler = self.add_prompt("Right Side Wall Filler",'DISTANCE',0) 
        right_filler = right_side_wall_filler.get_var("right_filler")
        bridge_left = self.add_prompt("Bridge Left",'CHECKBOX',False) 
        bridge_right = self.add_prompt("Bridge Right",'CHECKBOX',False) 
        left_bridge_shelf_width = self.add_prompt("Left Bridge Shelf Width",'DISTANCE',pc_unit.inch(12)) 
        right_bridge_shelf_width = self.add_prompt("Right Bridge Shelf Width",'DISTANCE',pc_unit.inch(12)) 
        # b_left = bridge_left.get_var("b_left")
        # b_right = bridge_right.get_var("b_right")
        # b_left_width = left_bridge_shelf_width.get_var("b_left_width")
        # b_right_width = right_bridge_shelf_width.get_var("b_right_width")
        
        self.add_opening_prompts()

        depth_1 = self.get_prompt("Opening 1 Depth").get_var("depth_1")
        height_1 = self.get_prompt("Opening 1 Height").get_var("height_1")
        floor_1 = self.get_prompt("Opening 1 Floor Mounted").get_var("floor_1")
        depth_last = self.get_prompt("Opening " + str(self.opening_qty) + " Depth").get_var("depth_last")
        height_last = self.get_prompt("Opening " + str(self.opening_qty) + " Height").get_var("height_last")
        floor_last = self.get_prompt("Opening " + str(self.opening_qty) + " Floor Mounted").get_var("floor_last")
        s_thickness = self.get_prompt("Shelf Thickness").get_var("s_thickness")

        left_side = data_closet_parts.add_closet_part(self)
        left_side.obj_bp["IS_PANEL_BP"] = True
        left_side.set_name('Left Panel')
        left_side.loc_x('left_filler',[left_filler])
        left_side.loc_y(value = 0)
        left_side.loc_z('IF(floor_1,0,height-height_1)',[floor_1,height,height_1])
        left_side.rot_y(value=math.radians(-90))
        left_side.rot_z(value=0)
        left_side.dim_x('height_1',[height_1])
        left_side.dim_y('-depth_1',[depth_1])
        left_side.dim_z('-panel_thickness_var',[panel_thickness_var])
        self.panels.append(left_side)
        bpy.context.view_layer.update()

        # self.add_left_blind_parts()

        previous_panel = None
        for i in range(1,self.opening_qty):
            if previous_panel == None:
                previous_panel = self.add_panel(i,left_side)
                self.panels.append(previous_panel)
            else:
                previous_panel = self.add_panel(i,previous_panel)
                self.panels.append(previous_panel)

        right_side = data_closet_parts.add_closet_part(self)
        right_side.obj_bp["IS_PANEL_BP"] = True
        right_side.set_name('Right Panel')
        right_side.loc_x('width-right_filler',[width,right_filler])
        right_side.loc_y(value = 0)
        right_side.loc_z('IF(floor_last,0,height-height_last)',[floor_last,height,height_last])
        right_side.rot_y(value=math.radians(-90))
        right_side.rot_z(value=0)
        right_side.dim_x('height_last',[height_last])
        right_side.dim_y('-depth_last',[depth_last])
        right_side.dim_z('panel_thickness_var',[panel_thickness_var])
        home_builder_utils.flip_normals(right_side)
        self.panels.append(right_side)

        bpy.context.view_layer.update()

        for index, panel in enumerate(self.panels):
            if index + 1 < len(self.panels):
                opening_height = self.get_prompt("Opening " + str(index+1) + " Height").get_var('opening_height')
                floor = self.get_prompt("Opening " + str(index+1) + " Floor Mounted").get_var('floor')
                remove_bottom = self.get_prompt("Remove Bottom " + str(index+1)).get_var('remove_bottom')

                bottom = self.add_shelf(index + 1,panel,self.panels[index+1])
                bottom.loc_z('IF(floor,closet_kick_height_var,height-opening_height)',[floor,closet_kick_height_var,height,opening_height])
                hide = bottom.get_prompt('Hide')
                hide.set_formula('remove_bottom',[remove_bottom])

                top = self.add_shelf(index + 1,panel,self.panels[index+1])
                top.loc_z('IF(floor,opening_height,height)-shelf_thickness_var',[floor,opening_height,height,shelf_thickness_var])

                kick = self.add_toe_kick(index + 1,panel,self.panels[index+1])

                opening = self.add_opening(index + 1,panel,self.panels[index+1])

        calculator = self.get_calculator('Opening Calculator')
        bpy.context.view_layer.update()
        calculator.calculate()
        print("Closet: Draw Time --- %s seconds ---" % (time.time() - start_time))