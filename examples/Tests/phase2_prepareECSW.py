# -*- coding: utf-8 -*-

from stlib.scene.wrapper import Wrapper
    
# Because sofa launcher create a template of our scene, we need to indicate the path to our original scene
import sys
import numpy as np

import phase1_snapshots

####################				PARAM 			  #########################

#### Run manually
# modesFilePath = "/home/felix/SOFA/plugin/ModelOrderReduction/examples/Tests/2_OUTPUT/2_Modes_Options/"
# modesFileName = "test_modes.txt"
# nbrOfNode = 28
# phase = [1,1,1,1]
##################

#### with launcher
modesFilePath = "$MODESFILEPATH"
modesFileName = "$MODESFILENAME"

phase = $PHASE
nbrOfModes = $NBROFMODES
periodSavedGIE = $PERIODSAVEDGIE
nbTrainingSet = $NBTRAININGSET
##################

paramForcefield = {
 	'name' : 'HyperReducedFEMForceField',
	'prepareECSW' : True,
	'modesPath': modesFilePath+modesFileName,
	'periodSavedGIE' : periodSavedGIE[0],
	'nbModes' : nbrOfModes,
	'nbTrainingSet' : nbTrainingSet} 

paramMappedMatrixMapping = {
	'template': 'Vec1d,Vec1d',
	'object1': '@./MechanicalObject',
	'object2': '@./MechanicalObject',
	'mappedForceField':'@./modelNode/HyperReducedFEMForceField',
	'mappedMass': '@./modelNode/UniformMass', # to change -> if name != Err
	'performECSW': False}

paramMORMapping = {
	'input': '@../MechanicalObject',
    'output': '@./MechanicalObject',  # to change -> if name != Err
    'modesPath': modesFilePath+modesFileName}

paramWrapper = {
	"/modelNode/TetrahedronFEMForceField" : {
						'paramForcefield': paramForcefield,
						'paramMORMapping': paramMORMapping,
						'paramMappedMatrixMapping': paramMappedMatrixMapping}			
	}

modesPositionStr = '0'
for i in range(1,nbrOfModes):
    modesPositionStr = modesPositionStr + ' 0'

###############################################################################

def MORNameExistance (name,kwargs):
    if 'name' in kwargs :
        if kwargs['name'] == name : 
        	return True

componentType = []*len(paramWrapper)
solverParam = [[]]*len(paramWrapper)
containers = []*len(paramWrapper)
def MORreplace(node,type,newParam,initialParam):
	global solverParam
	
	currentPath = node.getPathName()
	counter = 0
	for key in newParam :
		tabReduced = key.split('/')
		path = '/'.join(tabReduced[:-1])
		# print ('tabReduced : ',tabReduced)
		# print ('path : '+path)
		# print ('currenPath : '+currentPath)
		if currentPath == path :
			name = ''.join(tabReduced[-1:])
			# print ('name : '+name)

			# 	Find the differents solver to move them in order to have them before the MappedMatrixForceFieldAndMass
			if str(type).find('Solver') != -1 or type == 'EulerImplicit' or type == 'GenericConstraintCorrection':
				if 'name' in initialParam:
					solverParam[counter].append(initialParam['name'])
				else: 
					solverParam[counter].append(type)
			
			# 	Find loader to be able to save elements allowing to build the connectivity file
			if str(type).find('Loader') != -1:
				if 'name' in initialParam:
					containers.append(initialParam['name'])
				else: 
					containers.append(type)
			
			#	Change the initial Forcefield by the HyperReduced one with the new argument and save 
			if MORNameExistance(name,initialParam) or type == name:
				newParam[key]['paramForcefield']['poissonRatio'] = initialParam['poissonRatio']
				newParam[key]['paramForcefield']['youngModulus'] = initialParam['youngModulus']

				if name == 'TetrahedronFEMForceField':
					componentType.append('tetrahedra')
					return 'HyperReducedTetrahedronFEMForceField', newParam[key]['paramForcefield']
				elif name == 'TriangleFEMForceField':
					componentType.append('triangles')
					return 'HyperReducedTriangleFEMForceField', newParam[key]['paramForcefield']

		counter+=1

	return None

tmpFind = 0
def searchObjectAndDestroy(node,mySolver,newParam):
	global tmpFind

	for child in node.getChildren():
		currentPath = child.getPathName()
		counter = 0
		# print ('child Name : ',child.name)
		for key in newParam :
			tabReduced = key.split('/')
			path = '/'.join(tabReduced[:-1])
			# print ('path : '+path)
			# print ('currenPath : '+currentPath)
			if currentPath == path :
			
				myParent = child.getParents()[0]
				modelMOR = myParent.createChild(child.name+'_MOR')
				modelMOR.createObject('MechanicalObject',template='Vec1d',position=modesPositionStr)
				modelMOR.moveChild(child)

				for obj in child.getObjects():
					# print obj.name 
					if obj.name in mySolver[counter]:
						# print('To move!')
						child.removeObject(obj)
						child.getParents()[0].addObject(obj)

				# print 'Create new child modelMOR and move node in it'

				if 'paramMappedMatrixMapping' in newParam[key]:
					modelMOR.createObject('MappedMatrixForceFieldAndMass', **newParam[key]['paramMappedMatrixMapping'] )
					# print 'Create MappedMatrixForceFieldAndMass in modelMOR'

				if 'paramMORMapping' in newParam[key]:		
					child.createObject('ModelOrderReductionMapping', **newParam[key]['paramMORMapping'])
					# print "Create ModelOrderReductionMapping in node"
				
				tmpFind+=1

				if phase == [1]*len(phase):
					elements = child.getObject(containers[counter]).findData(componentType[counter]).value
					np.savetxt('saved_elements.txt', elements,fmt='%i')
					print "Saved elements"

			counter+=1	

		if tmpFind >= len(paramWrapper):
			# print ('yolo')
			return None

		else:
			searchObjectAndDestroy(child,mySolver,newParam)	

def createScene(rootNode):

	phase1_snapshots.createScene(Wrapper(rootNode, MORreplace, paramWrapper)) 
	# print ('Solver to move : 	'+str(solverParam))
	# print ('Containers : 		'+str(containers))
	# print ('ComponentType : 	'+str(componentType))

	searchObjectAndDestroy(rootNode,solverParam,paramWrapper)