-- Script Lua para DFHack 0.47.x: obtiene estado del juego como texto.
local lines = {}

-- Encontrar al aventurero.
-- En DFHack 0.47 adventure mode, el aventurero es siempre units.active[0].
local adv = nil
if #df.global.world.units.active > 0 then
    adv = df.global.world.units.active[0]
end

local function get_unit_name(u)
    if u.name and u.name.first_name ~= '' then
        return dfhack.TranslateName(u.name)
    end
    return '(sin nombre)'
end

local function get_race_id(u)
    local race_raw = df.global.world.raws.creatures.all[u.race]
    if race_raw then return race_raw.creature_id end
    return '???'
end

if adv then
    table.insert(lines, 'UNIT: ' .. get_unit_name(adv) .. ' (' .. get_race_id(adv) .. ')')
    table.insert(lines, 'POS: x=' .. adv.pos.x .. ' y=' .. adv.pos.y .. ' z=' .. adv.pos.z)
    table.insert(lines, 'HP: ' .. adv.body.blood_count .. '/' .. adv.body.blood_max)

    -- Necesidades vitales.
    local ok_needs, _ = pcall(function()
        table.insert(lines, 'HUNGER: ' .. adv.counters2.hunger_timer)
        table.insert(lines, 'THIRST: ' .. adv.counters2.thirst_timer)
        table.insert(lines, 'SLEEP: ' .. adv.counters2.sleepiness_timer)
    end)

    -- Heridas.
    table.insert(lines, 'WOUNDS: ' .. #adv.body.wounds)
else
    table.insert(lines, 'UNIT: (aventurero no encontrado)')
end

-- Fecha in-game.
local ok_date, _ = pcall(function()
    local year = df.global.cur_year
    local tick = df.global.cur_year_tick
    -- 1 mes = 33600 ticks, 1 día = 1200 ticks
    local month = math.floor(tick / 33600) + 1
    local day = math.floor((tick % 33600) / 1200) + 1
    table.insert(lines, string.format('DATE: %d-%02d-%02d', year, month, day))
end)

-- Focus (pantalla/menú actual).
local ok_focus, focus = pcall(dfhack.gui.getCurFocus)
if ok_focus and type(focus) == 'string' then
    table.insert(lines, 'FOCUS: ' .. focus)
elseif ok_focus and type(focus) == 'table' then
    table.insert(lines, 'FOCUS: ' .. table.concat(focus, ','))
else
    table.insert(lines, 'FOCUS: unknown')
end

-- Si hay conversación abierta, listar opciones.
local ok_conv, _ = pcall(function()
    local focus_str = ''
    if ok_focus then
        focus_str = type(focus) == 'string' and focus or table.concat(focus, ',')
    end
    if string.find(focus_str, 'Conversation') then
        local choices = df.global.ui_advmode.conversation.choices
        if choices and #choices > 0 then
            local opts = {}
            for i = 0, #choices - 1 do
                local c = choices[i]
                local title = tostring(c.title)
                if title and title ~= '' then
                    table.insert(opts, i .. ':' .. title)
                end
            end
            if #opts > 0 then
                table.insert(lines, 'CONV_CHOICES: ' .. table.concat(opts, '; '))
            end
        end
    end
end)

-- Ubicación: sitio (ciudad/fortaleza) y región.
if adv then
    local ok_loc, loc_err = pcall(function()
        local map = df.global.world.map
        local wd = df.global.world.world_data

        -- Posición global en embark tiles.
        local gx = math.floor(map.region_x + adv.pos.x / 48)
        local gy = math.floor(map.region_y + adv.pos.y / 48)

        -- Buscar si está dentro de un sitio.
        for k, v in pairs(wd.sites) do
            if gx >= v.pos.x * 16 + v.rgn_min_x and gx <= v.pos.x * 16 + v.rgn_max_x and
               gy >= v.pos.y * 16 + v.rgn_min_y and gy <= v.pos.y * 16 + v.rgn_max_y then
                table.insert(lines, 'SITE: ' .. dfhack.TranslateName(v.name, true))
                break
            end
        end

        -- Región desde region_map.
        local wx = math.floor(gx / 16)
        local wy = math.floor(gy / 16)
        if wx >= 0 and wx < wd.world_width and wy >= 0 and wy < wd.world_height then
            local tile = wd.region_map[wx]:_displace(wy)
            local region = wd.regions[tile.region_id]
            if region and region.name then
                local rname = dfhack.TranslateName(region.name, true)
                if rname ~= '' then
                    table.insert(lines, 'REGION: ' .. rname)
                end
            end
        end
    end)
    if not ok_loc then
        table.insert(lines, 'LOCATION: error (' .. tostring(loc_err) .. ')')
    end
end

-- Unidades cercanas al aventurero.
local nearby = {}
if adv then
    for i, u in ipairs(df.global.world.units.active) do
        if u ~= adv then
            local dist = math.abs(u.pos.x - adv.pos.x) + math.abs(u.pos.y - adv.pos.y)
            if dist < 15 and dist > 0 then
                local n = get_unit_name(u)
                local r = get_race_id(u)
                table.insert(nearby, n .. ' (' .. r .. ', d=' .. dist .. ')')
                if #nearby >= 8 then break end
            end
        end
    end
end
if #nearby > 0 then
    table.insert(lines, 'NEARBY: ' .. table.concat(nearby, '; '))
else
    table.insert(lines, 'NEARBY: (nadie cerca)')
end

print(table.concat(lines, '\n'))
