# drawing the Earth on equirectangular projection

import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import numpy
import matplotlib.ticker as mticker

fig = plt.figure(figsize=(64,32), frameon=False)
ax = fig.add_subplot(1,1,1, projection=ccrs.PlateCarree(central_longitude=180))

ax.set_global()
#ax.stock_img()
#ax.coastlines(resolution='50m')

ax.add_feature(cfeature.NaturalEarthFeature('physical', 'ocean', '50m', edgecolor='face', facecolor=cfeature.COLORS['water']))
ax.add_feature(cfeature.NaturalEarthFeature('physical', 'land', '50m', edgecolor='face', facecolor=cfeature.COLORS['land']))
ax.add_feature(cfeature.NaturalEarthFeature('physical', 'lakes', '50m', edgecolor='face', facecolor=cfeature.COLORS['water']))
ax.add_feature(cfeature.NaturalEarthFeature('physical', 'rivers_lake_centerlines', '50m', edgecolor=cfeature.COLORS['water'], facecolor='none'))
ax.add_feature(cfeature.NaturalEarthFeature('cultural', 'admin_0_countries', '50m', edgecolor='gray', facecolor='none'))

gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=False, linewidth=1, alpha=0.8)
gl.xlocator = mticker.FixedLocator(list(range(0,361,60)))
gl.ylocator = mticker.FixedLocator(list(range(-90,91,30)))

plt.subplots_adjust(left=0, right=1, bottom=0, top=1)
plt.savefig("earth-equirectanguler3.png", dpi=8192/64)
