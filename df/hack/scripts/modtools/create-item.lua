-- creates an item of a given type and material
--author expwnent
local usage = [====[

modtools/create-item
====================
Replaces the `createitem` plugin, with standard
arguments. The other versions will be phased out in a later version.

Arguments::

    -creator id
        specify the id of the unit who will create the item,
        or \\LAST to indicate the unit with id df.global.unit_next_id-1
        examples:
            0
            2
            \\LAST
    -material matstring
        specify the material of the item to be created
        examples:
            INORGANIC:IRON
            CREATURE_MAT:DWARF:BRAIN
            PLANT_MAT:MUSHROOM_HELMET_PLUMP:DRINK
    -item itemstr
        specify the itemdef of the item to be created
        examples:
            WEAPON:ITEM_WEAPON_PICK
    -quality qualitystr
        specify the quality level of the item to be created (df.item_quality)
        examples: Ordinary, WellCrafted, FinelyCrafted, Masterful, or 0-5
    -matchingShoes
        create two of this item
    -matchingGloves
        create two of this item, and set handedness appropriately

]====]
local utils = require 'utils'

local validArgs = utils.invert({
 'help',
 'creator',
 'material',
 'item',
-- 'creature',
-- 'caste',
 'leftHand',
 'rightHand',
 'matchingGloves',
 'matchingShoes',
 'quality'
})

local organicTypes = utils.invert({
 df.item_type.REMAINS,
 df.item_type.FISH,
 df.item_type.FISH_RAW,
 df.item_type.VERMIN,
 df.item_type.PET,
 df.item_type.EGG,
})

local badTypes = utils.invert({
 df.item_type.CORPSE,
 df.item_type.CORPSEPIECE,
 df.item_type.FOOD,
})

function createItem(creatorID, item, material, leftHand, rightHand, quality, matchingGloves, matchingShoes)
 local itemQuality = df.item_quality[quality] or tonumber(quality) or df.item_quality.Ordinary

 local creator = df.unit.find(creatorID)
 if not creator then
  error 'Invalid creator.'
 end

 if not item then
  error 'Invalid item.'
 end
 local itemType = dfhack.items.findType(item)
 if itemType == -1 then
  error 'Invalid item.'
 end
 local itemSubtype = dfhack.items.findSubtype(item)

 if organicTypes[itemType] then
  --TODO: look up creature and caste
  error 'Not yet supported.'
 end

 if badTypes[itemType] then
  error 'Not supported.'
 end

 if not material then
  error 'Invalid material.'
 end
 local materialInfo = dfhack.matinfo.find(material)
 if not materialInfo then
  error 'Invalid material.'
 end

 local item1 = dfhack.items.createItem(itemType, itemSubtype, materialInfo['type'], materialInfo.index, creator)
 local item = df.item.find(item1)

 item:setQuality(itemQuality)

 if matchingGloves then
  if not isGloves(item) then
   error "Passed -matchingGloves with non-glove item"
  end

  local item2 = dfhack.items.createItem(itemType, itemSubtype, materialInfo['type'], materialInfo.index, creator)
  local item_alt = df.item.find(item2)
  item.handedness[0] = 1
  item_alt.handedness[1] = 1
  item_alt:setQuality(itemQuality)
 end
 if matchingShoes then
  if not string.find(item.subtype.id, "ITEM_SHOES") then
   error "Passed -matchingShoes with non-shoe item"
  end

  local item3 = dfhack.items.createItem(itemType, itemSubtype, materialInfo['type'], materialInfo.index, creator)
  local item2_alt = df.item.find(item3)
  item2_alt:setQuality(itemQuality)
  end
end

if moduleMode then
 return
end

local args = utils.processArgs({...}, validArgs)

if args.help then
 print(usage)
 return
end

if args.creator == '\\LAST' then
  args.creator = tostring(df.global.unit_next_id-1)
end

function isGloves(i)
 for key,value in pairs(i) do
  if key == 'handedness' then
   return true
  end
 end
 return false
end

createItem(tonumber(args.creator), args.item, args.material, args.leftHand, args.rightHand, args.quality, args.matchingGloves, args.matchingShoes)
