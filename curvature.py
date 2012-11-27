from imposm.parser import OSMParser

# simple class that handles the parsed OSM data.
class CurvatureEvaluator(object):
	ways = []
	roads = ['secondary', 'residential', 'tertiary', 'primary', 'primary_link', 'motorway', 'motorway_link', 'road', 'trunk', 'trunk_link', 'unclassified']
	ignored_surfaces = ['dirt', 'unpaved', 'gravel', 'sand', 'grass', 'ground']
	coords = {}
	
	def coords_callback(self, coords):
		# callback method for coords
		for osm_id, lon, lat in coords:
			self.coords[osm_id] = {'lon': lon, 'lat': lat}
			if not (len(self.coords) % 10000):
				sys.stdout.write('-')
				sys.stdout.flush()

	def ways_callback(self, ways):
		# callback method for ways
		for osmid, tags, refs in ways:
			if 'highway' in tags and tags['highway'] in self.roads:				
				if 'name' not in tags:
					continue
				if refs[0] == refs[-1]:
					continue
				if 'surface' in tags and tags['surface'] in self.ignored_surfaces:
					continue
				
				way = {'id': osmid, 'type': tags['highway'], 'name':tags['name'], 'refs': refs}
				if 'tiger:county' in tags:
					way['county'] = tags['tiger:county']
				else:
					way['county'] = ''
				if 'surface' in tags:
					way['surface'] = tags['surface']
				else:
					way['surface'] = 'unknown'
				self.ways = self.ways + [way]
			if not (len(self.ways) % 1000):
				sys.stdout.write('.')
				sys.stdout.flush()
	
	def calculate(self):
		i = 0
		total = len(self.ways)
		if total < 100:
			marker = 1
		else:
			marker = round(len(self.ways)/100)
		
		for way in self.ways:
			i = i + 1
			if not (i % marker):
				sys.stdout.write('*')
				sys.stdout.flush()
			start = self.coords[way['refs'][0]]
			end = self.coords[way['refs'][-1]]
			way['distance'] = distance_on_unit_sphere(start['lat'], start['lon'], end['lat'], end['lon'])
			way['length'] = 0.0
			curvature = 0.0
			second = 0
			third = 0
			for ref in way['refs']:
				first = self.coords[ref]
				
				if not second:
					second = first
					continue
				
				first_second_length = distance_on_unit_sphere(first['lat'], first['lon'], second['lat'], second['lon'])
				way['length'] += first_second_length
				
				if not third:
					third = second
					second_third_length = first_second_length
					continue
				
				first_third_length = distance_on_unit_sphere(first['lat'], first['lon'], third['lat'], third['lon'])
				if first_third_length > 0:
					curvature += ((first_second_length + second_third_length) / first_third_length) - 1
				
				third = second
				second = first
				second_third_length = first_second_length
			if way['length'] > 0:
				way['curvature'] = curvature
			else:
				way['curvature'] = 0
		print ""
				

# From http://www.johndcook.com/python_longitude_latitude.html
import math
def distance_on_unit_sphere(lat1, long1, lat2, long2):
	if lat1 == lat2	 and long1 == long2:
		return 0

	# Convert latitude and longitude to 
	# spherical coordinates in radians.
	degrees_to_radians = math.pi/180.0
		
	# phi = 90 - latitude
	phi1 = (90.0 - lat1)*degrees_to_radians
	phi2 = (90.0 - lat2)*degrees_to_radians
		
	# theta = longitude
	theta1 = long1*degrees_to_radians
	theta2 = long2*degrees_to_radians
		
	# Compute spherical distance from spherical coordinates.
		
	# For two locations in spherical coordinates 
	# (1, theta, phi) and (1, theta, phi)
	# cosine( arc length ) = 
	#	 sin phi sin phi' cos(theta-theta') + cos phi cos phi'
	# distance = rho * arc length
	
	cos = (math.sin(phi1)*math.sin(phi2)*math.cos(theta1 - theta2) + 
		   math.cos(phi1)*math.cos(phi2))
	arc = math.acos( cos )

	# Remember to multiply arc by the radius of the earth 
	# in your favorite set of units to get length.
	return arc

# instantiate counter and parser and start parsing
evaluator = CurvatureEvaluator()
p = OSMParser(concurrency=4, ways_callback=evaluator.ways_callback, coords_callback=evaluator.coords_callback)

import sys
import os.path
if len(sys.argv) < 2: 
	sys.exit("Please pass the path of an osm file.")
filename = sys.argv[1]
if not os.path.isfile(filename):
	sys.exit("File doesn't exist: %s" % (filename))

p.parse(filename)
print " "
print "%d ways matched in %s, %d coordinates loaded." % (len(evaluator.ways), filename, len(evaluator.coords))
sys.stdout.flush()

# Loop through the ways and calculate their curvature
evaluator.calculate()
rad_earth = 3960 # Radius of the earth in miles

sorted_ways = sorted(evaluator.ways, key=lambda k: k['curvature'])
sorted_ways = filter(lambda w: w['length'] * rad_earth > 0.4 and w['name'] != '', sorted_ways)

print "Curvature	Length (mi) Distance (mi)	Id				Name  			County"
for way in sorted_ways:
	print '%9.1f	%9.2f	%9.2f	%10s	%25s	%20s' % (way['curvature'], way['length'] * rad_earth, way['distance'] * rad_earth, way['id'], way['name'], way['county'])
