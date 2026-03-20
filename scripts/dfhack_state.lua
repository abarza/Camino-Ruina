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
else
    table.insert(lines, 'UNIT: (aventurero no encontrado)')
end

local ok_focus, focus = pcall(dfhack.gui.getCurFocus)
if ok_focus and type(focus) == 'string' then
    table.insert(lines, 'FOCUS: ' .. focus)
elseif ok_focus and type(focus) == 'table' then
    table.insert(lines, 'FOCUS: ' .. table.concat(focus, ','))
else
    table.insert(lines, 'FOCUS: unknown')
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
