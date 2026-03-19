-- DFHack-native implementation of the classic Quickfort utility
--@module = true

local argparse = require('argparse')

-- reqscript all internal files here, even if they're not directly used by this
-- top-level file. this ensures modified transitive dependencies are properly
-- reloaded when this script is run.
local quickfort_aliases = reqscript('internal/quickfort/aliases')
local quickfort_api = reqscript('internal/quickfort/api')
local quickfort_build = reqscript('internal/quickfort/build')
local quickfort_building = reqscript('internal/quickfort/building')
local quickfort_command = reqscript('internal/quickfort/command')
local quickfort_common = reqscript('internal/quickfort/common')
local quickfort_config = reqscript('internal/quickfort/config')
local quickfort_dig = reqscript('internal/quickfort/dig')
local quickfort_keycodes = reqscript('internal/quickfort/keycodes')
local quickfort_list = reqscript('internal/quickfort/list')
local quickfort_map = reqscript('internal/quickfort/map')
local quickfort_meta = reqscript('internal/quickfort/meta')
local quickfort_notes = reqscript('internal/quickfort/notes')
local quickfort_orders = reqscript('internal/quickfort/orders')
local quickfort_parse = reqscript('internal/quickfort/parse')
local quickfort_place = reqscript('internal/quickfort/place')
local quickfort_preview = reqscript('internal/quickfort/preview')
local quickfort_query = reqscript('internal/quickfort/query')
local quickfort_reader = reqscript('internal/quickfort/reader')
local quickfort_set = reqscript('internal/quickfort/set')
local quickfort_transform = reqscript('internal/quickfort/transform')
local quickfort_zone = reqscript('internal/quickfort/zone')

-- public API
function apply_blueprint(params)
    local data, cursor = quickfort_api.normalize_data(params.data, params.pos)
    local ctx = quickfort_api.init_api_ctx(params, cursor)

    quickfort_common.verbose = not not params.verbose
    dfhack.with_finalize(
        function() quickfort_common.verbose = false end,
        function()
            for zlevel,grid in pairs(data) do
                quickfort_command.do_command_raw(params.mode, zlevel, grid, ctx)
            end
        end)
    return quickfort_api.clean_stats(ctx.stats)
end

-- interactive script
if dfhack_flags.module then
    return
end

local function do_help()
    print(dfhack.script_help())
end

local function do_gui(params)
    dfhack.run_script('gui/quickfort', table.unpack(params))
end

local action_switch = {
    set=quickfort_set.do_set,
    reset=quickfort_set.do_reset,
    list=quickfort_list.do_list,
    gui=do_gui,
    run=quickfort_command.do_command,
    orders=quickfort_command.do_command,
    undo=quickfort_command.do_command
}
setmetatable(action_switch, {__index=function() return do_help end})

local args = {...}
local action = table.remove(args, 1) or 'help'
args.commands = argparse.stringList(action)

local action_fn = action_switch[args.commands[1]]

if (action == 'run' or action == 'orders' or action == 'undo') and
        not dfhack.isMapLoaded() then
    qerror('quickfort needs a fortress map to be loaded.')
end

action_fn(args)
