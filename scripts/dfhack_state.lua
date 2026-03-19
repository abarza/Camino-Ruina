-- Script Lua para DFHack 53.x: obtiene estado del juego como texto.
local lines = {}

-- Encontrar al aventurero (último humano en lista, o por player_id).
local adv = nil
local pid = df.global.adventure.player_id
for i, u in ipairs(df.global.world.units.active) do
    if u.id == pid then
        adv = u
        break
    end
end
-- Fallback: buscar por nombre si player_id no matchea.
if not adv then
    for i = #df.global.world.units.active - 1, 0, -1 do
        local u = df.global.world.units.active[i]
        if dfhack.units.isCitizen(u) or df.creature_raw.find(u.race).creature_id == 'HUMAN' then
            adv = u
            break
        end
    end
end

if adv then
    local name = dfhack.units.getReadableName(adv)
    local race = df.creature_raw.find(adv.race).creature_id
    table.insert(lines, 'UNIT: ' .. name .. ' (' .. race .. ')')
    table.insert(lines, 'POS: x=' .. adv.pos.x .. ' y=' .. adv.pos.y .. ' z=' .. adv.pos.z)
    table.insert(lines, 'HP: ' .. adv.body.blood_count .. '/' .. adv.body.blood_max)
else
    table.insert(lines, 'UNIT: (aventurero no encontrado)')
end

local focus = dfhack.gui.getFocusStrings(df.global.gview.view.child)
table.insert(lines, 'FOCUS: ' .. table.concat(focus, ','))

-- Unidades cercanas al aventurero.
local nearby = {}
if adv then
    for i, u in ipairs(df.global.world.units.active) do
        if u ~= adv then
            local dist = math.abs(u.pos.x - adv.pos.x) + math.abs(u.pos.y - adv.pos.y)
            if dist < 15 and dist > 0 then
                local n = dfhack.units.getReadableName(u)
                local r = df.creature_raw.find(u.race).creature_id
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
