-- overlay plugin gui config
--@ module = true

local gui = require('gui')
local guidm = require('gui.dwarfmode')
local widgets = require('gui.widgets')

local overlay = require('plugins.overlay')

local DIALOG_WIDTH = 59
local LIST_HEIGHT = 14

local SHADOW_FRAME = copyall(gui.GREY_LINE_FRAME)
SHADOW_FRAME.signature_pen = false

local HIGHLIGHT_FRAME = copyall(SHADOW_FRAME)
HIGHLIGHT_FRAME.h_frame_pen = dfhack.pen.parse{ch=205, fg=COLOR_GREEN, bg=COLOR_BLACK}
HIGHLIGHT_FRAME.v_frame_pen = dfhack.pen.parse{ch=186, fg=COLOR_GREEN, bg=COLOR_BLACK}
HIGHLIGHT_FRAME.lt_frame_pen = dfhack.pen.parse{ch=201, fg=COLOR_GREEN, bg=COLOR_BLACK}
HIGHLIGHT_FRAME.lb_frame_pen = dfhack.pen.parse{ch=200, fg=COLOR_GREEN, bg=COLOR_BLACK}
HIGHLIGHT_FRAME.rt_frame_pen = dfhack.pen.parse{ch=187, fg=COLOR_GREEN, bg=COLOR_BLACK}
HIGHLIGHT_FRAME.rb_frame_pen = dfhack.pen.parse{ch=188, fg=COLOR_GREEN, bg=COLOR_BLACK}

local function make_highlight_frame_style(frame)
    local frame_style = copyall(HIGHLIGHT_FRAME)
    local fg, bg = COLOR_GREEN, COLOR_LIGHTGREEN
    if frame.t then
        frame_style.t_frame_pen = dfhack.pen.parse{ch=205, fg=fg, bg=bg}
    elseif frame.b then
        frame_style.b_frame_pen = dfhack.pen.parse{ch=205, fg=fg, bg=bg}
    end
    if frame.l then
        frame_style.l_frame_pen = dfhack.pen.parse{ch=186, fg=fg, bg=bg}
    elseif frame.r then
        frame_style.r_frame_pen = dfhack.pen.parse{ch=186, fg=fg, bg=bg}
    end
    return frame_style
end

--------------------
-- DraggablePanel --
--------------------

DraggablePanel = defclass(DraggablePanel, widgets.Panel)
DraggablePanel.ATTRS{
    name=DEFAULT_NIL,
    on_click=DEFAULT_NIL,
}

function DraggablePanel:init()
    self.is_dragging = false -- relative pos of the tile that we're dragging
end

function DraggablePanel:onInput(keys)
    if not keys._MOUSE_L_DOWN then return end
    local rect = self.frame_rect
    local x,y = self:getMousePos(gui.ViewRect{rect=rect})
    if not x then return end
    self.on_click()
    self.is_dragging = {x=x, y=y}
    return true
end

local function make_frame(old_frame, scr, scr_pos)
    local frame = copyall(old_frame)
    local ytop = scr_pos.y
    local xleft = scr_pos.x
    local ybottom = ytop + old_frame.h
    local xright = xleft + old_frame.w
    if ytop <= 0 then
        frame.t, frame.b = 0, nil
    elseif ybottom >= scr.height then
        frame.t, frame.b = nil, 0
    end
    if xleft <= 0 then
        frame.l, frame.r = 0, nil
    elseif xright >= scr.width then
        frame.l, frame.r = nil, 0
    end
    if frame.t then
        frame.t = math.max(-1, ytop)
    elseif frame.b then
        frame.b = math.max(-1, scr.height - ybottom)
    end
    if frame.l then
        frame.l = math.max(-1, xleft)
    elseif frame.r then
        frame.r = math.max(-1, scr.width - xright)
    end
    return frame
end

function DraggablePanel:update_position(scr_pos)
    local frame = make_frame(self.frame, self.frame_parent_rect, scr_pos)
    if self.frame.l == frame.l and self.frame.r == frame.r
            and self.frame.t == frame.t and self.frame.b == frame.b then
        return
    end
    self.frame = frame
    self.frame_style = make_highlight_frame_style(frame)
    self:updateLayout()
    local posx = frame.l and tostring(frame.l+2) or tostring(-(frame.r+2))
    local posy = frame.t and tostring(frame.t+2) or tostring(-(frame.b+2))
    overlay.overlay_command({'position', self.name, posx, posy}, true)
end

function DraggablePanel:onRenderFrame(dc, rect)
    if self.is_dragging then
        if df.global.enabler.mouse_lbut == 0 then
            self.is_dragging = false
        else
            local screenx, screeny = dfhack.screen.getMousePos()
            local scr_pos = {x=screenx - self.is_dragging.x,
                             y=screeny - self.is_dragging.y}
            self:update_position(scr_pos)
        end
    end
    if self:getMousePos(gui.ViewRect{rect=self.frame_rect}) then
        self.frame_background = dfhack.pen.parse{
                ch=32, fg=COLOR_LIGHTGREEN, bg=COLOR_LIGHTGREEN}
    else
        self.frame_background = nil
    end
    DraggablePanel.super.onRenderFrame(self, dc, rect)
end

-- called when this panel is being repositioned with the cursor keys
function DraggablePanel:cursor_move(keys)
    for code in pairs(keys) do
        local dx, dy = guidm.get_movement_delta(code, 1, 10)
        if dx then
            local scr_pos = {x=self.frame_rect.x1+dx, y=self.frame_rect.y1+dy}
            self:update_position(scr_pos)
            return true
        end
    end
end

-------------------
-- OverlayConfig --
-------------------

OverlayConfig = defclass(OverlayConfig, gui.Screen)

function OverlayConfig:init()
    -- prevent hotspot widgets from reacting
    overlay.register_trigger_lock_screen(self)

    self.scr_name = overlay.simplify_viewscreen_name(
            getmetatable(dfhack.gui.getCurViewscreen(true)))

    local main_panel = widgets.ResizingPanel{
        frame={w=DIALOG_WIDTH},
        frame_style=gui.GREY_LINE_FRAME,
        frame_title='Overlay config',
        frame_background=gui.CLEAR_PEN,
        frame_inset=1,
        autoarrange_subviews=true,
        autoarrange_gap=1,
    }
    main_panel:addviews{
        widgets.Label{text={'Current screen: ',
                            {text=self.scr_name, pen=COLOR_CYAN}}},
        widgets.CycleHotkeyLabel{
            view_id='filter',
            key='CUSTOM_CTRL_A',
            label='Showing:',
            options={{label='overlays for the current screen',
                    value='cur'},
                    {label='all overlays', value='all'}},
            on_change=self:callback('refresh_list')},
        widgets.FilteredList{
            view_id='list',
            frame={h=LIST_HEIGHT},
            on_select=self:callback('highlight_selected'),
            on_submit=self:callback('toggle_enabled'),
            on_submit2=self:callback('reposition'),
        },
        widgets.ResizingPanel{
            autoarrange_subviews=true,
            subviews={
                widgets.HotkeyLabel{
                    key='SELECT',
                    key_sep=' or click widget name to enable/disable',
                    scroll_keys={},
                },
                widgets.HotkeyLabel{
                    key='SEC_SELECT',
                    key_sep=' or drag the on-screen widget to reposition ',
                    scroll_keys={},
                },
                widgets.HotkeyLabel{
                    key='CUSTOM_CTRL_D',
                    scroll_keys={},
                    label='reset selected widget to its default position',
                    on_activate=self:callback('reset'),
                },
            },
        },
        widgets.WrappedLabel{
            scroll_keys={},
            text_to_wrap='When repositioning a widget, touch an edge of the'..
                ' screen to anchor the widget to that edge.',
        },
    }
    self:addviews{main_panel}
    self:refresh_list()
end

local function make_highlight_frame(widget_frame)
    local frame = {h=widget_frame.h+2, w=widget_frame.w+2}
    if widget_frame.l then frame.l = widget_frame.l - 1
    else frame.r = widget_frame.r - 1 end
    if widget_frame.t then frame.t = widget_frame.t - 1
    else frame.b = widget_frame.b - 1 end
    return frame
end

function OverlayConfig:refresh_list(filter)
    local choices = {}
    local state = overlay.get_state()
    local list = self.subviews.list
    local make_on_click_fn = function(idx)
        return function() list.list:setSelected(idx) end
    end
    for _,name in ipairs(state.index) do
        local db_entry = state.db[name]
        local widget = db_entry.widget
        if not widget.hotspot and filter ~= 'all' then
            local matched = false
            for _,scr in ipairs(overlay.normalize_list(widget.viewscreens)) do
                if overlay.simplify_viewscreen_name(scr) == self.scr_name then
                    matched = true
                    break
                end
            end
            if not matched then goto continue end
        end
        local panel = nil
        if not widget.overlay_only then
            panel = DraggablePanel{frame=make_highlight_frame(widget.frame),
                                   frame_style=SHADOW_FRAME,
                                   name=name,
                                   on_click=make_on_click_fn(#choices+1)}
        end
        local cfg = state.config[name]
        local tokens = {}
        table.insert(tokens, '[')
        table.insert(tokens, {
                pen=cfg.enabled and COLOR_LIGHTGREEN or COLOR_YELLOW,
                text=cfg.enabled and 'enabled' or 'disabled'})
        table.insert(tokens, (']%s '):format(cfg.enabled and ' ' or ''))
        table.insert(tokens, name)
        table.insert(tokens, {text=function()
                if self.reposition_panel and self.reposition_panel == panel then
                    return ' (repositioning)'
                end
                return ''
            end})
        table.insert(choices,
                {text=tokens, enabled=cfg.enabled, name=name, panel=panel,
                 search_key=name})
        ::continue::
    end
    local old_filter = list:getFilter()
    list:setChoices(choices)
    list:setFilter(old_filter)
    if self.frame_parent_rect then
        self:postUpdateLayout()
    end
end

function OverlayConfig:highlight_selected(_, obj)
    if self.selected_panel then
        self.selected_panel.frame_style = SHADOW_FRAME
        self.selected_panel = nil
    end
    self.reposition_panel = nil
    if not obj or not obj.panel then return end
    local panel = obj.panel
    panel.frame_style = make_highlight_frame_style(panel.frame)
    self.selected_panel = panel
end

function OverlayConfig:toggle_enabled(_, obj)
    local command = obj.enabled and 'disable' or 'enable'
    overlay.overlay_command({command, obj.name}, true)
    self:refresh_list(self.subviews.filter:getOptionValue())
end

function OverlayConfig:reposition(_, obj)
    self.reposition_panel = obj.panel
end

function OverlayConfig:reset()
    local idx,obj = self.subviews.list:getSelected()
    if not obj or not obj.panel then return end
    overlay.overlay_command({'position', obj.panel.name, 'default'}, true)
    self:refresh_list(self.subviews.filter:getOptionValue())
end

function OverlayConfig:onDismiss()
    view = nil
end

function OverlayConfig:postUpdateLayout()
    for _,choice in ipairs(self.subviews.list:getChoices()) do
        if choice.panel then
            choice.panel:updateLayout(self.frame_parent_rect)
        end
    end
end

function OverlayConfig:onInput(keys)
    if self.reposition_panel then
        if keys.LEAVESCREEN or keys.SELECT then
            self.reposition_panel = nil
            return true
        elseif self.reposition_panel:cursor_move(keys) then
            return true
        end
    end
    if keys.LEAVESCREEN then
        self:dismiss()
        return true
    end
    if self.selected_panel then
        if self.selected_panel:onInput(keys) then
            return true
        end
    end
    for _,choice in ipairs(self.subviews.list:getVisibleChoices()) do
        if choice.panel and choice.panel:onInput(keys) then
            return true
        end
    end
    return self:inputToSubviews(keys)
end

function OverlayConfig:onRenderFrame(dc, rect)
    self:renderParent()
    for _,choice in ipairs(self.subviews.list:getVisibleChoices()) do
        local panel = choice.panel
        if panel and panel ~= self.selected_panel then
            panel:render(dc)
        end
    end
    if self.selected_panel then
        self.render_selected_panel = function()
            self.selected_panel:render(dc)
        end
    else
        self.render_selected_panel = nil
    end
end

function OverlayConfig:renderSubviews(dc)
    OverlayConfig.super.renderSubviews(self, dc)
    if self.render_selected_panel then
        self.render_selected_panel()
    end
end

if dfhack_flags.module then
    return
end

view = view or OverlayConfig{}:show()
